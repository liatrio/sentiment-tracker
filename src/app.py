import atexit
import logging
import os
import re
import uuid  # For generating unique session IDs
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from slack_bolt import Ack, App, Respond
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from src.session_data import SessionData  # For creating new sessions
from src.session_store import ThreadSafeSessionStore
from src.slack_bot.handlers import handle_feedback_modal_submission
from src.slack_bot.views import open_feedback_modal  # For opening the modal

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
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    # Process all messages, not just those that mention the bot
    process_before_response=True,
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
        # Notify initiator that the session expired (best-effort)
        try:
            client.chat_postMessage(
                channel=initiator_user_id,
                text=(
                    f"Your feedback session *{session_id}* has reached its time limit and is now closed.\n"
                    "Thanks for using the feedback bot!"
                ),
            )
        except SlackApiError as exc:
            logger.warning(
                "Failed to send expiry DM for session %s: %s",
                session_id,
                exc.response["error"],
            )
        logger.info("Session %s expired and removed after time limit.", session_id)
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


# Pattern matching for hello messages (case insensitive)
@app.message(re.compile("hello", re.IGNORECASE))
def message_hello(message, say):
    # Say hello back
    logger.info(
        f"Received hello message from user {message['user']}"
        f" in channel {message.get('channel')}"
    )
    say(f"Hey there <@{message['user']}>!")


# Pattern matching for help messages (case insensitive)
@app.message(re.compile("help", re.IGNORECASE))
def message_help(message, say):
    logger.info(
        f"Received help request from user {message['user']}"
        f" in channel {message.get('channel')}"
    )
    help_text = (
        "*Available Commands:*\n"
        "• Say `hello` to get a greeting\n"
        "• Use `/ping` to check if I'm online\n"
        "• Use `@botname help` to see this message again\n"
        "• Try mentioning me with `@botname` to start a conversation"
    )
    say(help_text)


# Example command handler
@app.command("/ping")
def command_ping(ack, respond):
    # Acknowledge command request
    ack()
    logger.info("Received ping command")
    # Respond to the command
    respond("Pong! :table_tennis_paddle_and_ball:")


@app.command("/test-feedback")
def handle_test_feedback_command(ack, command, client, logger, respond):
    """Handles the /test-feedback slash command to open the feedback modal."""
    ack()
    try:
        user_id = command["user_id"]
        channel_id = command.get(
            "channel_id"
        )  # Might be None if used in DMs with the bot
        trigger_id = command["trigger_id"]

        # Generate a session ID first as it's needed for the modal's private_metadata
        session_id = str(uuid.uuid4())

        # Open the modal as soon as possible with the trigger_id
        open_feedback_modal(client=client, trigger_id=trigger_id, session_id=session_id)
        logger.info(
            f"Attempted to open feedback modal with session_id '{session_id}' for user '{user_id}'."
        )

        # Now, create and store the session data
        new_session = SessionData(
            session_id=session_id,
            initiator_user_id=user_id,  # The user who invoked /test-feedback
            channel_id=channel_id,
            target_user_ids=[
                user_id
            ],  # For /test-feedback, the target is the initiator
            time_limit_minutes=None,  # No specific time limit for /test-feedback by default
        )
        session_store.add_session(new_session)
        logger.info(f"Created and stored session '{session_id}' for user '{user_id}'.")

    except SlackApiError as e:
        logger.error(
            f"Error opening feedback modal for user '{user_id}': {e.response['error']}",
            exc_info=True,
        )
        respond(
            text="Sorry, something went wrong while trying to open the feedback form. Please try again."
        )
    except Exception as e:  # General fallback for other errors
        logger.error(
            f"Unexpected error in /test-feedback for user '{user_id}': {e}",
            exc_info=True,
        )
        respond(text="Sorry, an unexpected error occurred. Please try again.")


def process_gather_feedback_request(
    command: Dict[str, Any],
    client: WebClient,
    logger: logging.Logger,
    respond: Respond,
):
    """Processes the core logic of the /gather-feedback command in a background thread."""
    try:
        user_id = command["user_id"]
        command_text = command.get("text", "")
        logger.info(
            f"Processing /gather-feedback from user '{user_id}' with text: '{command_text}'"
        )

        # Regex to extract user group handle and optional time
        pattern = re.compile(
            r"for\s+<!subteam\^([A-Z0-9]+)\|@([^>]+)>(?:\s+in\s+(-?\d+)\s+minutes)?",
            re.IGNORECASE,
        )
        match = pattern.search(command_text)

        if not match:
            respond(
                "I'm sorry, I didn't understand that. Please use the format: `/gather-feedback for @user-group [in X minutes]`"
            )
            return

        user_group_id = match.group(1)
        user_group_handle = match.group(2)
        time_in_minutes_str = match.group(3)
        user_group_name_for_message = f"<!subteam^{user_group_id}|@{user_group_handle}>"

        # Validate and determine the session time
        time_in_minutes = 0
        if time_in_minutes_str:
            try:
                time_in_minutes = int(time_in_minutes_str)
                if time_in_minutes <= 0:
                    logger.warning(
                        f"Invalid time '{time_in_minutes_str}' for /gather-feedback by user '{user_id}'. Time must be a positive integer."
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
            f"Parsed for /gather-feedback from user '{user_id}': group_id='{user_group_id}', handle='{user_group_handle}', time: {time_in_minutes} minutes"
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
        )
        session_store.add_session(new_session)

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
            f"Error processing /gather-feedback request for user '{command.get('user_id', 'unknown')}': {e}",
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


@app.command("/gather-feedback")
def handle_gather_feedback_command(
    ack: Ack,
    command: Dict[str, Any],
    client: WebClient,
    logger: logging.Logger,
    respond: Respond,
):
    """Handles the /gather-feedback slash command to initiate feedback collection."""
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
            f"Submitted /gather-feedback request for user '{command['user_id']}' to thread pool."
        )

    except Exception as e:
        logger.error(
            f"Error submitting /gather-feedback for user '{command['user_id']}' to thread pool: {e}",
            exc_info=True,
        )
        respond("Sorry, there was an issue submitting your request. Please try again.")


# Example app mention handler
@app.event("app_mention")
def handle_app_mention(event, say):
    logger.info(f"Bot was mentioned by user {event['user']}")
    say(f"You mentioned me, <@{event['user']}>! How can I help?")


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


# NOTE: Runtime startup moved to src/main.py to keep this module import-safe and testable.
