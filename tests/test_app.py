# tests/test_app.py
import os
from unittest.mock import MagicMock, patch

import src.app as app
from src.app import process_gather_feedback_request  # Import the worker function
from src.app import (
    custom_error_handler,
    handle_app_mention,
    handle_gather_feedback_command,
    log_request,
)
from src.session_data import SessionData

# --- Basic Handlers and Middleware Tests (No Change) --- #


@patch("src.app.logger")
def test_handle_app_mention_handler(mock_logger):
    """Test that the handle_app_mention handler responds correctly."""
    mock_say = MagicMock()
    mock_event = {"user": "UAPPMENTION", "text": "@bot help"}
    handle_app_mention(event=mock_event, say=mock_say, logger=mock_logger)
    from src.app import _help_text

    mock_say.assert_called_once_with(_help_text())
    # help branch should not invoke debug logging
    mock_logger.debug.assert_not_called()


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
        f"Submitted {app.GATHER_FEEDBACK_COMMAND} request for user 'U_TESTER' to thread pool."
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
        f"Error submitting {app.GATHER_FEEDBACK_COMMAND} for user 'U_ERROR_USER' to thread pool: Pool is closed",
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
            f"Parsed for {app.GATHER_FEEDBACK_COMMAND} from user 'U_VALID_GROUP_ONLY': group_id='SGROUPID', handle='test-group', time: 5 minutes"
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
    @patch("src.slack_bot.utils.get_channel_members", return_value=["U1", "U2"])
    def test_channel_fallback_success(self, mock_members, mock_logger):
        """Fallback to channel members when no user group is given."""
        mock_respond = MagicMock()
        mock_client = MagicMock()
        command_payload = {
            "text": "on team morale for 3 minutes",
            "user_id": "U_INIT",
            "channel_id": "C123",
        }
        process_gather_feedback_request(
            command=command_payload,
            client=mock_client,
            respond=mock_respond,
            logger=mock_logger,
        )
        # Should call get_channel_members once
        mock_members.assert_called_once_with(mock_client, "C123")
        mock_respond.assert_called_once()

    @patch("src.app.logger")
    def test_invalid_format_totally_unparseable(self, mock_logger):
        """Ensure unparseable commands still show help."""
        mock_respond = MagicMock()
        command_payload = {"text": "foobar", "user_id": "U_BAD"}
        process_gather_feedback_request(
            command=command_payload,
            client=MagicMock(),
            respond=mock_respond,
            logger=mock_logger,
        )
        mock_respond.assert_called_once()

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
    def test_l_exception(self, mock_logger):
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
            f"Error processing {app.GATHER_FEEDBACK_COMMAND} request for user 'U_EXCEPTION': {test_exception}",
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
            f"Parsed for {app.GATHER_FEEDBACK_COMMAND} from user 'U_INITIATOR': group_id='SGROUPID', handle='group', time: 10 minutes"
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
