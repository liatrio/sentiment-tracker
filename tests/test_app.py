# tests/test_app.py
from unittest.mock import MagicMock, patch

# For now, let's assume we can test the decorated functions somewhat directly
# by calling them with mocked arguments.
from src.app import handle_test_feedback_command  # Added for testing
from src.app import (
    command_ping,
    custom_error_handler,
    handle_app_mention,
    log_request,
    message_hello,
    message_help,
)
from src.session_data import SessionData  # Added for type assertion

# Functions to test from src.app
# We need to be careful with how the app instance and its decorators are handled.
# For unit testing handlers, import them directly if standalone,
# or mock the app object if they rely on it heavily.


@patch("src.app.logger")  # Patch the logger in the app module
def test_message_hello_handler(mock_logger):
    """Test that the message_hello handler responds correctly."""
    # Arrange
    mock_say = MagicMock()
    test_user_id = "U123ABC"
    test_channel_id = "C456DEF"
    mock_message = {
        "user": test_user_id,
        "channel": test_channel_id,
        "text": "hello there bot",
    }

    # Act
    message_hello(message=mock_message, say=mock_say)

    # Assert
    mock_say.assert_called_once_with(f"Hey there <@{test_user_id}>!")
    mock_logger.info.assert_called_once_with(
        f"Received hello message from user {test_user_id} in channel {test_channel_id}"
    )


@patch("src.app.logger")  # Patch the logger in the app module
def test_message_help_handler(mock_logger):
    """Test that the message_help handler responds with help text."""
    # Arrange
    mock_say = MagicMock()
    test_user_id = "U123XYZ"
    test_channel_id = "C456PQR"
    mock_message = {
        "user": test_user_id,
        "channel": test_channel_id,
        "text": "help me please",
    }
    expected_help_text = (
        "*Available Commands:*\n"
        "• Say `hello` to get a greeting\n"
        "• Use `/ping` to check if I'm online\n"
        "• Use `@botname help` to see this message again\n"
        "• Try mentioning me with `@botname` to start a conversation"
    )

    # Act
    message_help(message=mock_message, say=mock_say)

    # Assert
    mock_say.assert_called_once_with(expected_help_text)
    mock_logger.info.assert_called_once_with(
        f"Received help request from user {test_user_id} in channel {test_channel_id}"
    )


@patch("src.app.logger")  # Patch the logger in the app module
def test_command_ping_handler(mock_logger):
    """Test that the command_ping handler acknowledges and responds."""
    # Arrange
    mock_ack = MagicMock()
    mock_respond = MagicMock()

    # Act
    command_ping(ack=mock_ack, respond=mock_respond)

    # Assert
    mock_ack.assert_called_once()
    mock_respond.assert_called_once_with("Pong! :table_tennis_paddle_and_ball:")
    mock_logger.info.assert_called_once_with("Received ping command")


@patch("src.app.logger")  # Patch the logger in the app module
def test_handle_app_mention_handler(mock_logger):
    """Test that the handle_app_mention handler responds correctly."""
    # Arrange
    mock_say = MagicMock()
    test_user_id = "UAPPMENTION"
    mock_event = {"user": test_user_id, "text": "@botname what can you do?"}

    # Act
    handle_app_mention(event=mock_event, say=mock_say)

    # Assert
    mock_say.assert_called_once_with(
        f"You mentioned me, <@{test_user_id}>! How can I help?"
    )
    mock_logger.info.assert_called_once_with(
        f"Bot was mentioned by user {test_user_id}"
    )


@patch("src.app.logger")  # Patch the logger in the app module
def test_log_request_middleware(
    mock_app_logger,
):  # Renamed to avoid conflict if we patch logger per test
    """Test that the log_request middleware logs the body and calls next."""
    # Arrange
    mock_next = MagicMock()
    mock_body = {"event": {"type": "message", "text": "test event"}}

    # Act
    # The middleware uses the logger passed to it (app.logger by default).
    # We patch src.app.logger, so the middleware uses this patched logger.
    log_request(logger=mock_app_logger, body=mock_body, next=mock_next)

    # Assert
    mock_app_logger.debug.assert_called_once_with(f"Received event: {mock_body}")
    mock_next.assert_called_once()


@patch("src.app.logger")  # Patch the logger in the app module
def test_custom_error_handler(mock_app_logger):
    """Test that the custom_error_handler logs the error and body."""
    # Arrange
    test_error = Exception("Test exception occurred")
    mock_body = {"event": {"type": "error_event", "text": "error details"}}
    # The custom_error_handler in src/app.py takes 'error', 'body', and 'logger'.

    # Act
    custom_error_handler(error=test_error, body=mock_body, logger=mock_app_logger)

    # Assert
    # Based on src/app.py, the handler uses logger.exception and logger.debug
    mock_app_logger.exception.assert_called_once_with(
        f"Error handling request: {test_error}"
    )
    mock_app_logger.debug.assert_called_once_with(f"Request body: {mock_body}")


# We can add more meaningful tests later for other handlers.


@patch("src.app.uuid.uuid4")
@patch("src.app.open_feedback_modal")
@patch("src.app.session_store")
@patch("src.app.logger")
def test_handle_test_feedback_command_success(
    mock_logger,
    mock_session_store,
    mock_open_feedback_modal,
    mock_uuid4,
):
    """Test successful execution of the /test-feedback command."""
    # Arrange
    mock_ack = MagicMock()
    mock_client = MagicMock()
    mock_respond = MagicMock()
    test_user_id = "U_TEST_USER"
    test_channel_id = "C_TEST_CHANNEL"
    test_trigger_id = "T_TEST_TRIGGER"
    test_session_id = "fake-uuid-1234"

    mock_uuid4.return_value = test_session_id

    mock_command_payload = {
        "user_id": test_user_id,
        "channel_id": test_channel_id,
        "trigger_id": test_trigger_id,
    }

    # Act
    handle_test_feedback_command(
        ack=mock_ack,
        command=mock_command_payload,
        client=mock_client,
        logger=mock_logger,
        respond=mock_respond,
    )

    # Assert
    mock_ack.assert_called_once()
    mock_uuid4.assert_called_once()

    # Check that session_store.add_session was called with a SessionData instance
    assert mock_session_store.add_session.call_count == 1
    added_session_arg = mock_session_store.add_session.call_args[0][0]
    assert isinstance(added_session_arg, SessionData)
    assert added_session_arg.session_id == test_session_id
    assert added_session_arg.user_id == test_user_id
    assert added_session_arg.channel_id == test_channel_id

    mock_logger.info.assert_any_call(
        f"Created new session '{test_session_id}' for /test-feedback command from user '{test_user_id}'."
    )
    mock_open_feedback_modal.assert_called_once_with(
        client=mock_client,
        trigger_id=test_trigger_id,
        session_id=test_session_id,
    )
    mock_logger.info.assert_any_call(
        f"Opened feedback modal for session '{test_session_id}' triggered by user '{test_user_id}'."
    )
    mock_respond.assert_not_called()


@patch(
    "src.app.uuid.uuid4"
)  # Still need to mock uuid even if it's not directly used before exception
@patch("src.app.open_feedback_modal")
@patch("src.app.session_store")
@patch("src.app.logger")
def test_handle_test_feedback_command_exception(
    mock_logger,
    mock_session_store,
    mock_open_feedback_modal,
    mock_uuid4,  # Keep mock_uuid4 in signature even if not used before exception
):
    """Test error handling in the /test-feedback command."""
    # Arrange
    mock_ack = MagicMock()
    mock_client = MagicMock()
    mock_respond = MagicMock()
    test_user_id = "U_TEST_USER_EXC"
    test_trigger_id = "T_TEST_TRIGGER_EXC"

    mock_command_payload = {
        "user_id": test_user_id,
        "trigger_id": test_trigger_id,
        # channel_id can be optional
    }

    # Configure a mock to raise an exception
    test_exception = Exception("Something broke")
    mock_session_store.add_session.side_effect = test_exception
    # or mock_open_feedback_modal.side_effect = test_exception, depending on what you want to test

    # Act
    handle_test_feedback_command(
        ack=mock_ack,
        command=mock_command_payload,
        client=mock_client,
        logger=mock_logger,
        respond=mock_respond,
    )

    # Assert
    mock_ack.assert_called_once()
    mock_logger.error.assert_called_once_with(
        f"Error handling /test-feedback command: {test_exception}", exc_info=True
    )
    mock_respond.assert_called_once_with(
        text="Sorry, something went wrong while trying to open the feedback form. Please try again."
    )
    mock_open_feedback_modal.assert_not_called()  # Should not be called if session creation failed
