import atexit
import logging
import os
import re
import uuid  # For generating unique session IDs

# Load environment variables
GATHER_FEEDBACK_COMMAND = os.getenv("GATHER_FEEDBACK_COMMAND", "/gather-feedback")
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from slack_bolt import Ack, App, Respond
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from src.session_data import SessionData  # For creating new sessions
from src.session_store import ThreadSafeSessionStore
from src.slack_bot.handlers import (  # For opening the modal and building invitation message
    handle_feedback_button_click,
    handle_feedback_modal_submission,
)
from src.slack_bot.views import (  # For opening the modal and building invitation message
    build_invitation_message,
)

from .scheduler import Scheduler

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging_level = os.environ.get("SLACK_LOG_LEVEL", "INFO")
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging_level
)
logger = logging.getLogger(__name__)

# Initialize the app with the bot token and enable message listening
# Determine if token verification should be disabled (useful for CI/test mode)
_token_verification_enabled_env = os.getenv(
    "SLACK_BOLT_TOKEN_VERIFICATION_ENABLED", "true"
).lower()
# Treat any value other than explicit "false" (case-insensitive) as truthy
_token_verification_enabled = _token_verification_enabled_env != "false"

app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    # Process all messages, not just those that mention the bot
    process_before_response=True,
    token_verification_enabled=_token_verification_enabled,
)


# Resolve max concurrent sessions (optional limit)
def _get_max_sessions_from_env() -> Optional[int]:  # noqa: WPS430 – tiny helper
    raw_val = os.getenv("MAX_CONCURRENT_SESSIONS")
    if not raw_val:
        return None
    try:
        parsed = int(raw_val)
        if parsed <= 0:
            logger.warning(
                "Ignoring MAX_CONCURRENT_SESSIONS=%s (must be positive int)", raw_val
            )
            return None
        return parsed
    except ValueError:
        logger.warning(
            "Invalid MAX_CONCURRENT_SESSIONS value '%s'; must be integer.", raw_val
        )
        return None


# Initialize session store with optional limit
session_store = ThreadSafeSessionStore(max_sessions=_get_max_sessions_from_env())

# Initialize a single thread pool for the application
executor = ThreadPoolExecutor(max_workers=10)

# Shared scheduler for non-blocking timers (e.g., session expiry reminders)
scheduler = Scheduler(executor)


# ------------------------------------------------------------------
# Expiry / reminder hooks
# ------------------------------------------------------------------


def _expire_feedback_session(
    session_id: str, initiator_user_id: str, client: WebClient
):
    """Callback run by Scheduler when a feedback session times out."""
    try:
        session = session_store.remove_session(session_id)
        if session is None:
            logger.debug("Expiry callback: session %s already removed", session_id)
            return

        # Build partial report if any feedback exists
        has_feedback = bool(session.feedback_items)

        # Post report (or just DM) target channel decision
        target_channel = session.channel_id or initiator_user_id

        if has_feedback:
            from src.reporting.aggregator import process_session  # local import
            from src.reporting.render import post_report_to_slack  # local import

            try:
                processed = process_session(session)
                post_report_to_slack(
                    processed=processed,
                    client=client,
                    channel=target_channel,
                )

            except Exception as exc:
                logger.error(
                    "Failed to post partial report for expired session %s: %s",
                    session_id,
                    exc,
                    exc_info=True,
                )

        # Notify initiator that the session expired (best-effort)
        try:
            note_extra = " Partial feedback report posted." if has_feedback else ""
            client.chat_postMessage(
                channel=initiator_user_id,
                text=(
                    f"Your feedback session *{session_id}* has reached its time limit and is now closed.{note_extra}"
                ),
            )
        except SlackApiError as exc:
            logger.warning(
                "Failed to send expiry DM for session %s: %s",
                session_id,
                exc.response.get("error"),
            )

        logger.info(
            "Session %s expired and removed after time limit. feedback_items=%d",
            session_id,
            len(session.feedback_items),
        )
    except Exception:  # pragma: no cover – ensure scheduler thread survives
        logger.exception("Error expiring session %s", session_id)


def _send_pending_reminder(session_id: str, client: WebClient) -> None:
    """DM pending users one minute before session expiry."""
    try:
        session = session_store.get_session(session_id)
        if session is None or session.is_complete:
            logger.debug("Reminder skipped for session %s (done/absent)", session_id)
            return
        failures = 0
        for user_id in list(session.pending_users):
            try:
                client.chat_postMessage(
                    channel=user_id,
                    text=(
                        "⏰ Friendly reminder: you have *1 minute* left to submit feedback "
                        f"for session `{session_id}`. Please open the modal and send your input!"
                    ),
                )
            except SlackApiError as exc:
                failures += 1
                logger.warning(
                    "Failed to send reminder DM to %s for session %s: %s",
                    user_id,
                    session_id,
                    exc.response["error"],
                )
        logger.info(
            "Sent 1-minute reminder for session %s to %d user(s) (%d failures)",
            session_id,
            len(session.pending_users),
            failures,
        )
    except Exception:  # pragma: no cover – ensure scheduler thread survives
        logger.exception("Error sending reminder for session %s", session_id)


def shutdown_executor():
    """Gracefully shut down scheduler and thread pool executor."""
    logger.info("Shutting down scheduler and thread pool executor...")
    # Stop scheduler first so it doesn't submit new tasks while executor is shutting down
    try:
        scheduler.shutdown()
    except Exception:  # pragma: no cover – ensure shutdown continues
        logger.exception("Error shutting down scheduler")

    executor.shutdown(wait=True)
    logger.info("Scheduler and thread pool executor shut down gracefully.")


# Register the shutdown function to be called on exit
atexit.register(shutdown_executor)


# Log all incoming messages to help with debugging
@app.middleware
def log_request(logger, body, next):
    logger.debug(f"Received event: {body}")
    return next()


def _help_text() -> str:
    """Return a rich help message describing bot purpose and usage."""

    return (
        "*Sentiment-Bot – Quick, Anonymous Team Feedback*\n\n"
        "This bot lets you collect short, candid feedback and see an anonymised summary in minutes.\n\n"
        "*Core commands*\n"
        "• `@sentiment-bot help` — show this message.\n"
        f"• `{GATHER_FEEDBACK_COMMAND} from <@user-group> [on <topic>] [for <minutes> minutes|mins?]` — DM **only** members of the given user-group.\n"
        f"• `{GATHER_FEEDBACK_COMMAND} on <topic> [for <minutes> minutes|mins?]` — DM **everyone in the current channel**.\n\n"
        "**Examples:**\n"
        f"• `{GATHER_FEEDBACK_COMMAND} from @design` — ask @design for feedback (defaults to 5 min).\n"
        f"• `{GATHER_FEEDBACK_COMMAND} on last week's retro` — poll the whole channel about last week's retro (5 min).\n"
        f"• `{GATHER_FEEDBACK_COMMAND} from @frontend on sprint 42 for 15 minutes` — target @frontend, topic *sprint 42*, 15 min window.\n"
    )


# 1. Catch any mention of the bot
@app.event("app_mention")
def handle_app_mention(event, say, logger: logging.Logger):
    """
    Respond to `@sentiment-bot help`.
    Any other mention is ignored (or you can add more logic below).
    """
    text = event.get("text", "").lower()
    if "help" in text:
        say(_help_text())
    else:
        logger.debug("Ignoring mention without help: %s", text)


def process_gather_feedback_request(
    command: Dict[str, Any],
    client: WebClient,
    logger: logging.Logger,
    respond: Respond,
):
    """Processes the core logic of the gather-feedback command in a background thread."""
    try:
        user_id = command["user_id"]
        command_text = command.get("text", "")
        logger.info(
            f"Processing {GATHER_FEEDBACK_COMMAND} from user '{user_id}' with text: '{command_text}'",
        )

        # Matches:
        #   from|for <@usergroup> [on <reason>] [for|in <minutes> minutes]
        # The *reason* should capture everything after "on" up to the time
        # portion (if present) **or** the end of the string.  We achieve this
        # with a *look-ahead* that stops the match when we encounter the time
        # segment or the end of the string.
        pattern = re.compile(
            r"(?:from|for)\s+<!subteam\^([A-Z0-9]+)\|@([^>]+)>"  # group ID + handle
            r"(?:\s+on\s+(.*?)(?=\s+(?:for|in)\s+-?\d+\s+(?:minutes?|mins?)|$))?"  # reason (optional)
            r"(?:\s+(?:for|in)\s+(-?\d+)\s+(?:minutes?|mins?))?",  # time (optional, allow negative for validation)
            re.IGNORECASE,
        )
        match = pattern.search(command_text)

        if not match:
            # ------------------------------------------------------------------
            # Fallback: gather feedback from the *whole channel*.
            # Expected syntax:
            #   on <reason> [for|in <minutes> minutes]
            # The leading "on" is required to avoid ambiguity with future
            # extensions, but we accept it being omitted to keep UX smooth.
            # ------------------------------------------------------------------
            channel_pattern = re.compile(
                r"(?:on\s+)?(.*?)(?:\s+(?:for|in)\s+(-?\d+)\s+(?:minutes?|mins?))?$",
                re.IGNORECASE,
            )
            ch_match = channel_pattern.search(command_text)
            if not ch_match:
                respond(
                    f"I'm sorry, I didn't understand that. Use either `{GATHER_FEEDBACK_COMMAND} from @user-group [for X min]` "
                    f"or `{GATHER_FEEDBACK_COMMAND} on <reason> [for X min]`"
                )
                return

            reason_raw = ch_match.group(1)
            time_in_minutes_str = ch_match.group(2)
            reason = reason_raw.strip() if reason_raw else None

            # Validate time (reuse logic)
            time_in_minutes = 0
            if time_in_minutes_str:
                try:
                    time_in_minutes = int(time_in_minutes_str)
                    if time_in_minutes <= 0:
                        logger.warning(
                            f"Invalid time '{time_in_minutes_str}' for {GATHER_FEEDBACK_COMMAND} by user '{user_id}'. Time must be positive."
                        )
                        respond("The time must be a positive number of minutes.")
                        return
                except ValueError:
                    logger.warning(
                        f"Invalid time format '{time_in_minutes_str}' for {GATHER_FEEDBACK_COMMAND} by user '{user_id}'."
                    )
                    respond("Oops! The time specified must be a valid number.")
                    return
            else:
                default_session_minutes_str = os.environ.get(
                    "DEFAULT_SESSION_MINUTES", "5"
                )
                try:
                    time_in_minutes = int(default_session_minutes_str)
                    if time_in_minutes <= 0:
                        logger.error(
                            f"Invalid DEFAULT_SESSION_MINUTES '{default_session_minutes_str}'. Falling back to 5."
                        )
                        time_in_minutes = 5
                except (ValueError, TypeError):
                    logger.error(
                        f"Invalid DEFAULT_SESSION_MINUTES '{default_session_minutes_str}'. Falling back to 5 minutes."
                    )
                    time_in_minutes = 5

            channel_id = command.get("channel_id")
            try:
                from src.slack_bot.utils import get_channel_members

                member_user_ids = get_channel_members(client, channel_id)
                if not member_user_ids:
                    respond(
                        "I couldn't find any active members in this channel to invite."
                    )
                    return
            except SlackApiError as exc:
                logger.error(
                    "Failed to fetch channel members for %s: %s",
                    channel_id,
                    exc,
                    exc_info=True,
                )
                respond(
                    "Sorry, I wasn't able to fetch channel members. Please try again later."
                )
                return

            # Reuse common session creation logic.
            session_id = str(uuid.uuid4())
            initiator_user_id = user_id

            new_session = SessionData(
                session_id=session_id,
                initiator_user_id=initiator_user_id,
                channel_id=channel_id,
                target_user_ids=member_user_ids,
                time_limit_minutes=time_in_minutes,
                reason=reason,
            )
            session_store.add_session(new_session)

            invite_blocks = build_invitation_message(
                session_id=session_id,
                initiator_user_id=initiator_user_id,
                channel_id=channel_id,
                reason=reason,
            )
            failures = 0
            for target_user_id in member_user_ids:
                try:
                    client.chat_postMessage(
                        channel=target_user_id,
                        text="You have been invited to provide feedback.",
                        blocks=invite_blocks,
                    )
                except SlackApiError as exc:
                    failures += 1
                    logger.warning(
                        "Failed to send feedback invitation to %s in session %s: %s",
                        target_user_id,
                        session_id,
                        exc.response.get("error", str(exc)),
                    )

            # Schedule expiry & reminders
            delay_seconds = time_in_minutes * 60
            scheduler.schedule(
                delay_seconds,
                _expire_feedback_session,
                session_id,
                initiator_user_id,
                client,
            )
            if delay_seconds > 60:
                scheduler.schedule(
                    delay_seconds - 60,
                    _send_pending_reminder,
                    session_id,
                    client,
                )

            respond(
                f"Okay, I've initiated a feedback session (ID: {session_id}) with {len(member_user_ids)} participant(s) "
                f"for {time_in_minutes} minutes. I'll reach out to them shortly."
            )
            return

        user_group_id = match.group(1)
        user_group_handle = match.group(2)
        reason_raw = match.group(3)  # May be None
        time_in_minutes_str = match.group(4)
        user_group_name_for_message = f"<!subteam^{user_group_id}|@{user_group_handle}>"

        # Clean up reason (strip trailing/leading whitespace) if provided
        reason = reason_raw.strip() if reason_raw else None

        # Validate and determine the session time
        time_in_minutes = 0
        if time_in_minutes_str:
            try:
                time_in_minutes = int(time_in_minutes_str)
                if time_in_minutes <= 0:
                    logger.warning(
                        f"Invalid time '{time_in_minutes_str}' for {GATHER_FEEDBACK_COMMAND} by user '{user_id}'. Time must be a positive integer."
                    )
                    respond("The time must be a positive number of minutes.")
                    return
            except ValueError:
                logger.warning(
                    f"Invalid time format '{time_in_minutes_str}' for /gather-feedback by user '{user_id}'."
                )
                respond("Oops! The time specified must be a valid number.")
                return
        else:
            default_session_minutes_str = os.environ.get("DEFAULT_SESSION_MINUTES", "5")
            try:
                time_in_minutes = int(default_session_minutes_str)
                if time_in_minutes <= 0:
                    logger.error(
                        f"Invalid DEFAULT_SESSION_MINUTES '{default_session_minutes_str}'. Must be a positive integer. Falling back to 5."
                    )
                    time_in_minutes = 5
            except (ValueError, TypeError):
                logger.error(
                    f"Invalid DEFAULT_SESSION_MINUTES '{default_session_minutes_str}'. Falling back to 5 minutes."
                )
                time_in_minutes = 5

        logger.info(
            f"Parsed for {GATHER_FEEDBACK_COMMAND} from user '{user_id}': group_id='{user_group_id}', handle='{user_group_handle}', time: {time_in_minutes} minutes"
        )
        if reason:
            logger.info(
                f"Parsed for {GATHER_FEEDBACK_COMMAND} from user '{user_id}': reason='{reason}'",
            )

        # Fetch user IDs from the user group
        try:
            member_user_ids = client.usergroups_users_list(usergroup=user_group_id)[
                "users"
            ]
            if not member_user_ids:
                respond(
                    f"The user group {user_group_name_for_message} doesn't have any members."
                )
                return
        except SlackApiError as e:
            logger.error(
                f"Error getting members for group '{user_group_id}': {e.response['error']}",
                exc_info=True,
            )
            if e.response["error"] == "subteam_not_found":
                respond(
                    f"Sorry, I can't find a user group with the handle {user_group_name_for_message}. Please double-check the group handle."
                )
            elif e.response["error"] == "missing_scope":
                respond(
                    "I don't have the necessary permissions to access user group information. Please check my app settings."
                )
            else:
                respond(
                    f"Sorry, an error occurred while trying to get members for {user_group_name_for_message}."
                )
            return

        # Create and store the feedback session
        session_id = str(uuid.uuid4())
        initiator_user_id = command["user_id"]
        channel_id = command.get("channel_id")

        new_session = SessionData(
            session_id=session_id,
            initiator_user_id=initiator_user_id,
            channel_id=channel_id,
            target_user_ids=member_user_ids,
            time_limit_minutes=time_in_minutes,
            reason=reason,
        )
        session_store.add_session(new_session)

        # DM each participant with invitation button
        invite_blocks = build_invitation_message(
            session_id=session_id,
            initiator_user_id=initiator_user_id,
            channel_id=channel_id,
            reason=reason,
        )
        failures = 0
        for target_user_id in member_user_ids:
            try:
                client.chat_postMessage(
                    channel=target_user_id,
                    text="You have been invited to provide feedback.",
                    blocks=invite_blocks,
                )
                logger.info(
                    "feedback_invitation_sent",
                    extra={"session_id": session_id, "target_user_id": target_user_id},
                )
            except SlackApiError as exc:
                failures += 1
                logger.warning(
                    "Failed to send feedback invitation to %s in session %s: %s",
                    target_user_id,
                    session_id,
                    exc.response.get("error", str(exc)),
                )

        # Schedule automatic session expiry
        delay_seconds = time_in_minutes * 60
        scheduler.schedule(
            delay_seconds,
            _expire_feedback_session,
            session_id,
            initiator_user_id,
            client,
        )
        # Schedule 1-minute reminder if time allows (>60s)
        if delay_seconds > 60:
            scheduler.schedule(
                delay_seconds - 60,
                _send_pending_reminder,
                session_id,
                client,
            )

        time_desc_for_log = f"{time_in_minutes} minutes"
        logger.info(
            f"Created and stored session '{session_id}' for user group '{user_group_name_for_message}' "
            f"initiated by '{initiator_user_id}'. {len(member_user_ids)} member(s), "
            f"time limit: {time_desc_for_log}."
        )

        time_message_segment = f"for {time_in_minutes} minutes"
        respond(
            f"Okay, I've initiated a feedback session (ID: {session_id}) for "
            f"{user_group_name_for_message} (with {len(member_user_ids)} member(s)), "
            f"{time_message_segment}. I'll reach out to them shortly."
        )

    except Exception as e:
        logger.error(
            f"Error processing {GATHER_FEEDBACK_COMMAND} request for user '{command.get('user_id', 'unknown')}': {e}",
            exc_info=True,
        )
        respond(
            "Sorry, an unexpected error occurred while processing your request. Please try again."
        )


# ------------------------------------------------------------------
# Thread helper utilities
# ------------------------------------------------------------------


def _log_future_exception(fut: Future) -> None:  # noqa: WPS430 – small util
    """Logs any exception raised by a completed *Future*."""
    exc = fut.exception()
    if exc is not None:
        logger.exception("Background task raised an exception: %s", exc, exc_info=exc)


def submit_background(func, /, *args, **kwargs) -> Future:  # noqa: WPS110
    """Submit *func* to the shared thread pool with automatic error logging."""

    fut = executor.submit(func, *args, **kwargs)
    fut.add_done_callback(_log_future_exception)
    return fut


@app.command(GATHER_FEEDBACK_COMMAND)
def handle_gather_feedback_command(
    ack: Ack,
    command: Dict[str, Any],
    client: WebClient,
    logger: logging.Logger,
    respond: Respond,
):
    """Handles the gather-feedback slash command to initiate feedback collection."""
    ack()
    try:
        # Submit the long-running task to the thread pool
        submit_background(
            process_gather_feedback_request,
            command=command,
            client=client,
            logger=logger,
            respond=respond,
        )
        logger.info(
            f"Submitted {GATHER_FEEDBACK_COMMAND} request for user '{command['user_id']}' to thread pool."
        )

    except Exception as e:
        logger.error(
            f"Error submitting {GATHER_FEEDBACK_COMMAND} for user '{command['user_id']}' to thread pool: {e}",
            exc_info=True,
        )
        respond("Sorry, there was an issue submitting your request. Please try again.")


# Error handler
@app.error
def custom_error_handler(error, body, logger):
    logger.exception(f"Error handling request: {error}")
    logger.debug(f"Request body: {body}")


# Register view submission handler for the feedback modal
@app.view("feedback_modal_callback")
def feedback_modal_submission_handler_wrapper(ack, body, client, view, logger):
    handle_feedback_modal_submission(
        ack=ack,
        body=body,
        client=client,
        view=view,
        logger=logger,
        session_store=session_store,
    )


# Register action handler for "Provide Feedback" button
@app.action("open_feedback_modal")
def feedback_button_click_wrapper(
    ack, body, client, logger
):  # noqa: WPS110 – slack signature
    handle_feedback_button_click(
        ack=ack,
        body=body,
        client=client,
        logger=logger,
        session_store=session_store,
    )


# NOTE: Runtime startup moved to src/main.py to keep this module import-safe and testable.
