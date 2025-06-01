import os
import logging
import re
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging_level = os.environ.get("SLACK_LOG_LEVEL", "INFO")
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging_level)
logger = logging.getLogger(__name__)

# Initialize the app with the bot token and enable message listening
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    # Process all messages, not just those that mention the bot
    process_before_response=True
)

# Log all incoming messages to help with debugging
@app.middleware
def log_request(logger, body, next):
    logger.debug(f"Received event: {body}")
    return next()

# Pattern matching for hello messages (case insensitive)
@app.message(re.compile("hello", re.IGNORECASE))
def message_hello(message, say):
    # Say hello back
    logger.info(f"Received hello message from user {message['user']} in channel {message.get('channel')}")
    say(f"Hey there <@{message['user']}>!")

# Pattern matching for help messages (case insensitive)
@app.message(re.compile("help", re.IGNORECASE))
def message_help(message, say):
    logger.info(f"Received help request from user {message['user']} in channel {message.get('channel')}")
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

# Main entry point for the app
if __name__ == "__main__":
    logger.info("Starting the Slack bot app...")
    try:
        # Start the app using Socket Mode
        handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
        logger.info("Socket Mode handler initialized")
        logger.info("Bot is ready to receive messages. Try sending 'hello' in a channel where the bot is invited.")
        handler.start()
    except Exception as e:
        logger.error(f"Error starting the app: {e}")
        logger.error("Make sure both SLACK_BOT_TOKEN and SLACK_APP_TOKEN are correct in your .env file")
        logger.error("Also verify the bot has been invited to the channel and has the necessary scopes")
        raise

