import logging
import os
import re
import uuid  # For generating unique session IDs
from typing import Any, Dict

from dotenv import load_dotenv
from slack_bolt import Ack, App, Respond
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from src.session_data import SessionData  # For creating new sessions
from src.session_store import ThreadSafeSessionStore
from src.slack_bot.handlers import handle_feedback_modal_submission
from src.slack_bot.views import open_feedback_modal  # For opening the modal

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

# Initialize session store
session_store = ThreadSafeSessionStore()


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
        user_id = command["user_id"]
        command_text = command.get("text", "")
        logger.info(
            f"Received /gather-feedback command with text: '{command_text}' from user '{user_id}'"
        )

        # Regex to capture user group ID, handle (optional), and time (optional)
        # Format: <!subteam^USERGROUP_ID|@handle> [in X minutes]
        # Group 1: USERGROUP_ID (e.g., S06154498F7)
        # Group 2: @handle (e.g., @dev-team) - optional
        # Group 3: Time in minutes (e.g., 30) - optional
        match = re.fullmatch(
            r"<!subteam\^([A-Z0-9]+)(?:\|(@[\w-]+))?>(?:\s+in\s+(-?\d+)\s+minutes)?",
            command_text.strip(),
        )

        if not match:
            logger.warning(
                f"Invalid format for /gather-feedback '{command_text}' by user '{user_id}'. Usage: /gather-feedback @user-group [in X minutes]"
            )
            respond(
                "Sorry, that command format isn't right. Please use: `/gather-feedback @user-group [in X minutes]` (e.g., `/gather-feedback @design-team in 60 minutes`). Make sure to select the user group from the suggestions."
            )
            return

        user_group_id = match.group(1)
        user_group_handle = match.group(2)  # Might be None if not provided by Slack
        time_in_minutes_str = match.group(3)

        user_group_name_for_message = (
            user_group_handle if user_group_handle else user_group_id
        )

        time_in_minutes = None

        if time_in_minutes_str:
            try:
                time_in_minutes = int(time_in_minutes_str)
                if time_in_minutes <= 0:
                    logger.warning(
                        f"Invalid time '{time_in_minutes_str}' for /gather-feedback by user '{command['user_id']}'. Time must be a positive integer."
                    )
                    respond("The time limit must be a positive number of minutes.")
                    return
            except ValueError:
                logger.warning(
                    f"Invalid non-numeric time value '{time_in_minutes_str}' for /gather-feedback from user '{user_id}'."
                )
                respond("The time specified must be a number (e.g., '30').")
                return
        else:  # No time was specified in the command
            default_session_minutes_str = os.environ.get("DEFAULT_SESSION_MINUTES", "5")
            try:
                time_in_minutes = int(default_session_minutes_str)
                if time_in_minutes <= 0:
                    logger.warning(
                        f"Invalid DEFAULT_SESSION_MINUTES value '{default_session_minutes_str}' (must be positive), defaulting to 5 minutes."
                    )
                    time_in_minutes = 5
                # Log that default is being used, after successfully setting it.
                logger.info(
                    f"Parsed for /gather-feedback from user '{user_id}': group_id='{user_group_id}', handle='{user_group_handle}', time not specified, using default: {time_in_minutes} minutes"
                )
            except ValueError:
                logger.warning(
                    f"Invalid DEFAULT_SESSION_MINUTES format '{default_session_minutes_str}' (must be an integer), defaulting to 5 minutes."
                )
                time_in_minutes = 5
                logger.info(
                    f"Parsed for /gather-feedback from user '{user_id}': group_id='{user_group_id}', handle='{user_group_handle}', time not specified, using fallback default: {time_in_minutes} minutes"
                )

        try:
            usergroup_members_response = client.usergroups_users_list(
                usergroup=user_group_id
            )
            member_user_ids = usergroup_members_response.get("users", [])
            if not member_user_ids:
                logger.warning(
                    f"User group '{user_group_name_for_message}' (ID: {user_group_id}) has no members or is invalid."
                )
                respond(
                    f"The user group {user_group_name_for_message} doesn't seem to have any members. Please check the group or try a different one."
                )
                return
            logger.info(
                f"Found {len(member_user_ids)} members in group '{user_group_name_for_message}' (ID: {user_group_id}): {member_user_ids}"
            )
        except SlackApiError as e:
            logger.error(
                f"Slack API error fetching members for user group ID '{user_group_id}': {e.response['error']}",
                exc_info=True,
            )
            if e.response["error"] == "usergroup_not_found":
                respond(
                    f"Sorry, I couldn't find the user group {user_group_name_for_message}. Please make sure it's a valid group."
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
        channel_id = command["channel_id"]

        new_session = SessionData(
            session_id=session_id,
            initiator_user_id=initiator_user_id,  # User who initiated
            channel_id=channel_id,  # Channel where the command was invoked
            target_user_ids=member_user_ids,  # List of user IDs from the group
            time_limit_minutes=time_in_minutes,  # Optional time limit
            # TODO: Add other relevant fields to SessionData if needed e.g. original_command_text
        )
        session_store.add_session(new_session)
        # time_in_minutes should now always have a value (either user-provided or default)
        time_desc_for_log = f"{time_in_minutes} minutes"
        logger.info(
            f"Created and stored session '{session_id}' for user group '{user_group_name_for_message}' "
            f"initiated by '{initiator_user_id}'. {len(member_user_ids)} member(s), "
            f"time limit: {time_desc_for_log}."
        )

        # time_in_minutes should now always have a value
        time_message_segment = f"for {time_in_minutes} minutes"
        respond(
            f"Okay, I've initiated a feedback session (ID: {session_id}) for "
            f"{user_group_name_for_message} (with {len(member_user_ids)} member(s)), "
            f"{time_message_segment}. I'll reach out to them shortly."
        )

        # TODO: Implement further steps:
        # 1. Logic to DM each user in member_user_ids to collect feedback.
        # 2. Set a timer for session expiration and reminders based on time_in_minutes.

    except Exception as e:
        logger.error(
            f"Error handling /gather-feedback command for user '{command.get('user_id', 'unknown')}': {e}",
            exc_info=True,
        )
        respond(
            "Sorry, an unexpected error occurred while processing your request. Please try again."
        )


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


# Main entry point for the app
if __name__ == "__main__":  # pragma: no cover
    logger.info("Starting the Slack bot app...")
    try:
        # Start the app using Socket Mode
        handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
        logger.info("Socket Mode handler initialized")
        logger.info(
            "Bot is ready to receive messages. "
            "Try sending 'hello' in a channel where the bot is invited."
        )
        handler.start()
    except Exception as e:
        logger.error(f"Error starting the app: {e}")
        logger.error(
            "Make sure both SLACK_BOT_TOKEN and SLACK_APP_TOKEN are correct"
            " in your .env file"
        )
        logger.error(
            "Also verify the bot has been invited to the channel"
            " and has the necessary scopes"
        )
        raise
