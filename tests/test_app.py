# tests/test_app.py
import os
from unittest.mock import ANY, MagicMock, patch

from src.app import process_gather_feedback_request  # Import the worker function
from src.app import (
    command_ping,
    custom_error_handler,
    handle_app_mention,
    handle_gather_feedback_command,
    handle_test_feedback_command,
    log_request,
    message_hello,
    message_help,
)
from src.session_data import SessionData

# --- Basic Handlers and Middleware Tests (No Change) --- #


@patch("src.app.logger")
def test_message_hello_handler(mock_logger):
    """Test that the message_hello handler responds correctly."""
    mock_say = MagicMock()
    mock_message = {"user": "U123ABC", "channel": "C456DEF", "text": "hello"}
    message_hello(message=mock_message, say=mock_say)
    mock_say.assert_called_once_with("Hey there <@U123ABC>!")
    mock_logger.info.assert_called_once_with(
        "Received hello message from user U123ABC in channel C456DEF"
    )


@patch("src.app.logger")
def test_message_help_handler(mock_logger):
    """Test that the message_help handler responds with help text."""
    mock_say = MagicMock()
    mock_message = {"user": "U123XYZ", "channel": "C456PQR", "text": "help"}
    expected_help_text = (
        "*Available Commands:*\n"
        "• Say `hello` to get a greeting\n"
        "• Use `/ping` to check if I'm online\n"
        "• Use `@botname help` to see this message again\n"
        "• Try mentioning me with `@botname` to start a conversation"
    )
    message_help(message=mock_message, say=mock_say)
    mock_say.assert_called_once_with(expected_help_text)
    mock_logger.info.assert_called_once_with(
        "Received help request from user U123XYZ in channel C456PQR"
    )


@patch("src.app.logger")
def test_command_ping_handler(mock_logger):
    """Test that the command_ping handler acknowledges and responds."""
    mock_ack = MagicMock()
    mock_respond = MagicMock()
    command_ping(ack=mock_ack, respond=mock_respond)
    mock_ack.assert_called_once()
    mock_respond.assert_called_once_with("Pong! :table_tennis_paddle_and_ball:")
    mock_logger.info.assert_called_once_with("Received ping command")


@patch("src.app.logger")
def test_handle_app_mention_handler(mock_logger):
    """Test that the handle_app_mention handler responds correctly."""
    mock_say = MagicMock()
    mock_event = {"user": "UAPPMENTION", "text": "@bot"}
    handle_app_mention(event=mock_event, say=mock_say)
    mock_say.assert_called_once_with(
        "You mentioned me, <@UAPPMENTION>! How can I help?"
    )
    mock_logger.info.assert_called_once_with("Bot was mentioned by user UAPPMENTION")


@patch("src.app.logger")
def test_log_request_middleware(mock_app_logger):
    """Test that the log_request middleware logs the body and calls next."""
    mock_next = MagicMock()
    mock_body = {"event": {"type": "message"}}
    log_request(logger=mock_app_logger, body=mock_body, next=mock_next)
    mock_app_logger.debug.assert_called_once_with(f"Received event: {mock_body}")
    mock_next.assert_called_once()


@patch("src.app.logger")
def test_custom_error_handler(mock_app_logger):
    """Test that the custom_error_handler logs the error and body."""
    test_error = ValueError("Test error")
    mock_body = {"event": {"type": "app_mention"}}
    custom_error_handler(error=test_error, body=mock_body, logger=mock_app_logger)
    mock_app_logger.exception.assert_called_once_with(
        f"Error handling request: {test_error}"
    )
    mock_app_logger.debug.assert_called_once_with(f"Request body: {mock_body}")


# --- Tests for /gather-feedback Command Handler --- #


@patch("src.app.executor")
@patch("src.app.logger")
def test_handle_gather_feedback_command_submits_to_executor(mock_logger, mock_executor):
    """Test that handle_gather_feedback_command submits the worker to the executor."""
    mock_ack = MagicMock()
    mock_respond = MagicMock()
    mock_client = MagicMock()
    command_payload = {"user_id": "U_TESTER"}

    handle_gather_feedback_command(
        ack=mock_ack,
        command=command_payload,
        client=mock_client,
        logger=mock_logger,
        respond=mock_respond,
    )

    mock_ack.assert_called_once()
    mock_executor.submit.assert_called_once_with(
        process_gather_feedback_request,
        command=command_payload,
        client=mock_client,
        logger=mock_logger,
        respond=mock_respond,
    )
    mock_logger.info.assert_called_once_with(
        "Submitted /gather-feedback request for user 'U_TESTER' to thread pool."
    )


@patch("src.app.executor")
@patch("src.app.logger")
def test_handle_gather_feedback_command_submission_error(mock_logger, mock_executor):
    """Test error handling when executor.submit fails."""
    mock_ack = MagicMock()
    mock_respond = MagicMock()
    command_payload = {"user_id": "U_ERROR_USER"}
    test_exception = Exception("Pool is closed")
    mock_executor.submit.side_effect = test_exception

    handle_gather_feedback_command(
        ack=mock_ack,
        command=command_payload,
        client=MagicMock(),
        logger=mock_logger,
        respond=mock_respond,
    )

    mock_ack.assert_called_once()
    mock_respond.assert_called_once_with(
        "Sorry, there was an issue submitting your request. Please try again."
    )
    mock_logger.error.assert_called_once_with(
        "Error submitting /gather-feedback for user 'U_ERROR_USER' to thread pool: Pool is closed",
        exc_info=True,
    )


# --- Tests for process_gather_feedback_request Worker Function --- #


class TestProcessGatherFeedbackRequest:
    """Test suite for the process_gather_feedback_request worker function."""

    @patch("src.app.uuid.uuid4")
    @patch("src.app.session_store")
    @patch("src.app.logger")
    def test_success_group_only(self, mock_logger, mock_session_store, mock_uuid4):
        """Test successful processing with user group only."""
        mock_respond = MagicMock()
        mock_client = MagicMock()
        mock_client.usergroups_users_list.return_value = {
            "users": ["U_MEMBER1", "U_MEMBER2"]
        }
        session_id = "test-session-id-group-only"
        mock_uuid4.return_value = session_id
        command_payload = {
            "text": "for <!subteam^SGROUPID|@test-group>",
            "user_id": "U_VALID_GROUP_ONLY",
            "channel_id": "C_CHANNEL1",
        }

        with patch.dict(os.environ, {"DEFAULT_SESSION_MINUTES": "5"}, clear=True):
            process_gather_feedback_request(
                command=command_payload,
                client=mock_client,
                respond=mock_respond,
                logger=mock_logger,
            )

        mock_respond.assert_called_once_with(
            f"Okay, I've initiated a feedback session (ID: {session_id}) for "
            "<!subteam^SGROUPID|@test-group> (with 2 member(s)), "
            "for 5 minutes. I'll reach out to them shortly."
        )
        assert mock_session_store.add_session.call_count == 1
        added_session = mock_session_store.add_session.call_args[0][0]
        assert isinstance(added_session, SessionData)
        assert added_session.session_id == session_id
        assert added_session.time_limit_minutes == 5  # Default time
        mock_logger.info.assert_any_call(
            "Parsed for /gather-feedback from user 'U_VALID_GROUP_ONLY': group_id='SGROUPID', handle='test-group', time: 5 minutes"
        )

    @patch("src.app.uuid.uuid4")
    @patch("src.app.session_store")
    @patch("src.app.logger")
    def test_success_group_and_time(self, mock_logger, mock_session_store, mock_uuid4):
        """Test successful processing with user group and time."""
        mock_client = MagicMock()
        mock_client.usergroups_users_list.return_value = {"users": ["U_MEMBER3"]}
        mock_respond = MagicMock()
        mock_uuid4.return_value = "fake-uuid-time"
        command_payload = {
            "text": "for <!subteam^SGROUPID|@group> in 10 minutes",
            "user_id": "U_INITIATOR",
            "channel_id": "C_CHANNEL",
        }
        process_gather_feedback_request(
            command=command_payload,
            client=mock_client,
            respond=mock_respond,
            logger=mock_logger,
        )
        mock_session_store.add_session.assert_called_once()
        added_session = mock_session_store.add_session.call_args[0][0]
        assert added_session.time_limit_minutes == 10
        mock_respond.assert_called_once_with(
            "Okay, I've initiated a feedback session (ID: fake-uuid-time) for "
            "<!subteam^SGROUPID|@group> (with 1 member(s)), "
            "for 10 minutes. I'll reach out to them shortly."
        )

    @patch("src.app.logger")
    def test_invalid_format_missing_group(self, mock_logger):
        """Test processing with invalid format (missing user group)."""
        mock_respond = MagicMock()
        command_payload = {"text": "in 10 minutes", "user_id": "U_INVALID_FORMAT"}
        process_gather_feedback_request(
            command=command_payload,
            client=MagicMock(),
            respond=mock_respond,
            logger=mock_logger,
        )
        mock_respond.assert_called_once_with(
            "I'm sorry, I didn't understand that. Please use the format: `/gather-feedback from @user-group [for X min]`"
        )

    @patch("src.app.logger")
    def test_invalid_time_negative(self, mock_logger):
        """Test processing with negative minutes."""
        mock_respond = MagicMock()
        command_payload = {
            "text": "for <!subteam^SGROUPID|@group> in -10 minutes",
            "user_id": "U_INVALID_TIME",
        }
        process_gather_feedback_request(
            command=command_payload,
            client=MagicMock(),
            respond=mock_respond,
            logger=mock_logger,
        )
        mock_respond.assert_called_once_with(
            "The time must be a positive number of minutes."
        )
        mock_logger.warning.assert_called_once()

    @patch("src.app.logger")
    def test_general_exception(self, mock_logger):
        """Test general exception handling during processing."""
        mock_respond = MagicMock()
        mock_client = MagicMock()
        test_exception = Exception("API is down")
        mock_client.usergroups_users_list.side_effect = test_exception
        command_payload = {
            "text": "for <!subteam^SGROUPID|@group>",
            "user_id": "U_EXCEPTION",
        }
        process_gather_feedback_request(
            command=command_payload,
            client=mock_client,
            respond=mock_respond,
            logger=mock_logger,
        )
        mock_respond.assert_called_once_with(
            "Sorry, an unexpected error occurred while processing your request. Please try again."
        )
        mock_logger.error.assert_called_once_with(
            f"Error processing /gather-feedback request for user 'U_EXCEPTION': {test_exception}",
            exc_info=True,
        )

    @patch.dict(os.environ, {"DEFAULT_SESSION_MINUTES": "10"}, clear=True)
    @patch("src.app.uuid.uuid4")
    @patch("src.app.session_store")
    @patch("src.app.logger")
    def test_default_time_env_var_set(
        self, mock_logger, mock_session_store, mock_uuid4
    ):
        """Test worker uses DEFAULT_SESSION_MINUTES when no time is specified."""
        mock_client = MagicMock()
        mock_client.usergroups_users_list.return_value = {"users": ["U_MEMBERX"]}
        command_payload = {
            "text": "for <!subteam^SGROUPID|@group>",
            "user_id": "U_INITIATOR",
            "channel_id": "C_CHANNEL2",
        }
        process_gather_feedback_request(
            command=command_payload,
            client=mock_client,
            respond=MagicMock(),
            logger=mock_logger,
        )
        added_session = mock_session_store.add_session.call_args[0][0]
        assert added_session.time_limit_minutes == 10
        mock_logger.info.assert_any_call(
            "Parsed for /gather-feedback from user 'U_INITIATOR': group_id='SGROUPID', handle='group', time: 10 minutes"
        )


# --- Tests for Executor Shutdown --- #


@patch("src.app.atexit.register")
def test_shutdown_executor_registered(mock_register):
    """Test that the shutdown_executor function is registered with atexit."""
    # Since atexit.register is called at import time, we need to reload the module
    # to test the registration call.
    import importlib

    import src.app

    importlib.reload(src.app)

    mock_register.assert_called_once_with(src.app.shutdown_executor)


# --- Tests for /test-feedback Command (No Change) --- #


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
    mock_ack = MagicMock()
    mock_client = MagicMock()
    mock_respond = MagicMock()
    mock_command_payload = {
        "user_id": "U_TEST_USER",
        "channel_id": "C_TEST_CHANNEL",
        "trigger_id": "T_TEST_TRIGGER",
    }
    test_session_id = "fake-uuid-1234"
    mock_uuid4.return_value = test_session_id

    handle_test_feedback_command(
        ack=mock_ack,
        command=mock_command_payload,
        client=mock_client,
        logger=mock_logger,
        respond=mock_respond,
    )

    mock_ack.assert_called_once()
    mock_open_feedback_modal.assert_called_once_with(
        client=mock_client,
        trigger_id="T_TEST_TRIGGER",
        session_id=test_session_id,
    )
    mock_session_store.add_session.assert_called_once_with(ANY)
    added_session_arg = mock_session_store.add_session.call_args[0][0]
    assert isinstance(added_session_arg, SessionData)
    assert added_session_arg.session_id == test_session_id


@patch("src.app.uuid.uuid4")
@patch("src.app.open_feedback_modal")
@patch("src.app.session_store")
@patch("src.app.logger")
def test_handle_test_feedback_command_exception(
    mock_logger,
    mock_session_store,
    mock_open_feedback_modal,
    mock_uuid4,
):
    """Test error handling in the /test-feedback command."""
    mock_ack = MagicMock()
    mock_client = MagicMock()
    mock_respond = MagicMock()
    mock_command_payload = {"user_id": "U_TEST_USER_EXC", "trigger_id": "T_TRIGGER"}
    test_exception = Exception("Something broke")
    mock_session_store.add_session.side_effect = test_exception

    handle_test_feedback_command(
        ack=mock_ack,
        command=mock_command_payload,
        client=mock_client,
        logger=mock_logger,
        respond=mock_respond,
    )

    mock_ack.assert_called_once()
    mock_logger.error.assert_called_once_with(
        f"Unexpected error in /test-feedback for user 'U_TEST_USER_EXC': {test_exception}",
        exc_info=True,
    )
    mock_respond.assert_called_once_with(
        text="Sorry, an unexpected error occurred. Please try again."
    )
