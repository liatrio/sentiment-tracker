# tests/test_app.py
import os
from unittest.mock import MagicMock, patch

# For now, let's assume we can test the decorated functions somewhat directly
# by calling them with mocked arguments.
from src.app import (  # Added for testing
    command_ping,
    custom_error_handler,
    handle_app_mention,
    handle_gather_feedback_command,
    handle_test_feedback_command,
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


@patch("src.app.uuid.uuid4")
@patch("src.app.session_store")
@patch("src.app.logger")
def test_handle_gather_feedback_command_success_group_only(
    mock_logger, mock_session_store, mock_uuid4
):
    """Test successful /gather-feedback with user group only."""
    mock_ack = MagicMock()
    mock_respond = MagicMock()
    mock_client = MagicMock()
    mock_client.usergroups_users_list = MagicMock(
        return_value={
            "ok": True,
            "users": ["U_MEMBER1", "U_MEMBER2"],
        }
    )
    command_payload = {
        "user_id": "U_VALID_GROUP_ONLY",
        "text": "<!subteam^SGROUPID|@test-group>",
        "channel_id": "C_VALID_GROUP_ONLY",
    }

    handle_gather_feedback_command(
        ack=mock_ack,
        command=command_payload,
        client=mock_client,
        logger=mock_logger,
        respond=mock_respond,
    )

    mock_ack.assert_called_once()
    mock_logger.info.assert_any_call(
        "Received /gather-feedback command with text: '<!subteam^SGROUPID|@test-group>' from user 'U_VALID_GROUP_ONLY'"
    )
    mock_logger.info.assert_any_call(
        "Parsed for /gather-feedback from user 'U_VALID_GROUP_ONLY': group_id='SGROUPID', handle='@test-group', time not specified, using default: 5 minutes"
    )
    mock_uuid4.assert_called_once()
    test_session_id = str(mock_uuid4.return_value)

    # Check session_store.add_session call
    assert mock_session_store.add_session.call_count == 1
    added_session_arg = mock_session_store.add_session.call_args[0][0]
    assert isinstance(added_session_arg, SessionData)
    assert added_session_arg.session_id == test_session_id
    assert added_session_arg.initiator_user_id == "U_VALID_GROUP_ONLY"
    assert added_session_arg.channel_id == "C_VALID_GROUP_ONLY"
    mock_client.usergroups_users_list.assert_called_once_with(usergroup="SGROUPID")
    assert added_session_arg.target_user_ids == ["U_MEMBER1", "U_MEMBER2"]
    assert (
        added_session_arg.time_limit_minutes == 5
    )  # Default time is 5 minutes when DEFAULT_SESSION_MINUTES is not set

    mock_respond.assert_called_once_with(
        f"Okay, I've initiated a feedback session (ID: {test_session_id}) for @test-group (with 2 member(s)), for 5 minutes. I'll reach out to them shortly."
    )
    mock_logger.info.assert_any_call(
        f"Created and stored session '{test_session_id}' for user group '@test-group' initiated by 'U_VALID_GROUP_ONLY'. 2 member(s), time limit: 5 minutes."
    )


@patch("src.app.uuid.uuid4")
@patch("src.app.session_store")
@patch("src.app.logger")
def test_handle_gather_feedback_command_success_group_and_time(
    mock_logger, mock_session_store, mock_uuid4
):
    """Test successful /gather-feedback with user group and time."""
    mock_ack = MagicMock()
    mock_respond = MagicMock()
    mock_client = MagicMock()
    mock_client.usergroups_users_list = MagicMock(
        return_value={
            "ok": True,
            "users": ["U_MEMBER3"],
        }
    )
    command_payload = {
        "user_id": "U_VALID_GROUP_TIME",
        "text": "<!subteam^SGROUPID|@test-group> in 30 minutes",
        "channel_id": "C_VALID_GROUP_TIME",
    }

    handle_gather_feedback_command(
        ack=mock_ack,
        command=command_payload,
        client=mock_client,
        logger=mock_logger,
        respond=mock_respond,
    )

    mock_ack.assert_called_once()
    mock_logger.info.assert_any_call(
        "Received /gather-feedback command with text: '<!subteam^SGROUPID|@test-group> in 30 minutes' from user 'U_VALID_GROUP_TIME'"
    )
    mock_uuid4.assert_called_once()
    test_session_id = str(mock_uuid4.return_value)

    # Check session_store.add_session call
    assert mock_session_store.add_session.call_count == 1
    added_session_arg = mock_session_store.add_session.call_args[0][0]
    assert isinstance(added_session_arg, SessionData)
    assert added_session_arg.session_id == test_session_id
    assert added_session_arg.initiator_user_id == "U_VALID_GROUP_TIME"
    assert added_session_arg.channel_id == "C_VALID_GROUP_TIME"
    mock_client.usergroups_users_list.assert_called_once_with(usergroup="SGROUPID")
    assert added_session_arg.target_user_ids == ["U_MEMBER3"]
    assert added_session_arg.time_limit_minutes == 30

    mock_respond.assert_called_once_with(
        f"Okay, I've initiated a feedback session (ID: {test_session_id}) for @test-group (with 1 member(s)), for 30 minutes. I'll reach out to them shortly."
    )
    mock_logger.info.assert_any_call(
        f"Created and stored session '{test_session_id}' for user group '@test-group' initiated by 'U_VALID_GROUP_TIME'. 1 member(s), time limit: 30 minutes."
    )


@patch("src.app.logger")
def test_handle_gather_feedback_command_invalid_format_missing_group(mock_logger):
    """Test /gather-feedback with invalid format (missing user group)."""
    mock_ack = MagicMock()
    mock_respond = MagicMock()
    mock_client = MagicMock()
    command_payload = {
        "user_id": "U_MISSING_GROUP",
        "text": "in 30 minutes",  # Missing @group
    }

    handle_gather_feedback_command(
        ack=mock_ack,
        command=command_payload,
        client=mock_client,
        logger=mock_logger,
        respond=mock_respond,
    )

    mock_ack.assert_called_once()
    mock_logger.warning.assert_called_once_with(
        f"Invalid format for /gather-feedback '{command_payload['text']}' by user 'U_MISSING_GROUP'. Usage: /gather-feedback @user-group [in X minutes]"
    )
    mock_respond.assert_called_once_with(
        "Sorry, that command format isn't right. Please use: `/gather-feedback @user-group [in X minutes]` (e.g., `/gather-feedback @design-team in 60 minutes`). Make sure to select the user group from the suggestions."
    )


@patch("src.app.logger")
def test_handle_gather_feedback_command_invalid_format_no_at_symbol(mock_logger):
    """Test /gather-feedback with invalid format (no @ symbol for group)."""
    mock_ack = MagicMock()
    mock_respond = MagicMock()
    mock_client = MagicMock()
    command_payload = {
        "user_id": "U_NO_AT_SYMBOL",
        "text": "team-no-at",
    }

    handle_gather_feedback_command(
        ack=mock_ack,
        command=command_payload,
        client=mock_client,
        logger=mock_logger,
        respond=mock_respond,
    )

    mock_ack.assert_called_once()
    mock_logger.warning.assert_called_once_with(
        "Invalid format for /gather-feedback 'team-no-at' by user 'U_NO_AT_SYMBOL'. Usage: /gather-feedback @user-group [in X minutes]"
    )
    mock_respond.assert_called_once_with(
        "Sorry, that command format isn't right. Please use: `/gather-feedback @user-group [in X minutes]` (e.g., `/gather-feedback @design-team in 60 minutes`). Make sure to select the user group from the suggestions."
    )


@patch("src.app.logger")
def test_handle_gather_feedback_command_invalid_time_non_numeric(mock_logger):
    """Test /gather-feedback with invalid non-numeric time."""
    mock_ack = MagicMock()
    mock_respond = MagicMock()
    mock_client = MagicMock()
    command_payload = {
        "user_id": "U_INVALID_TIME_NONNUM",
        "text": "<!subteam^S1234567890|@test-group> in thirty minutes",
    }

    handle_gather_feedback_command(
        ack=mock_ack,
        command=command_payload,
        client=mock_client,
        logger=mock_logger,
        respond=mock_respond,
    )

    mock_ack.assert_called_once()
    expected_log_message = f"Invalid format for /gather-feedback '{command_payload['text']}' by user 'U_INVALID_TIME_NONNUM'. Usage: /gather-feedback @user-group [in X minutes]"
    mock_logger.warning.assert_called_once_with(expected_log_message)
    expected_response_message = "Sorry, that command format isn't right. Please use: `/gather-feedback @user-group [in X minutes]` (e.g., `/gather-feedback @design-team in 60 minutes`). Make sure to select the user group from the suggestions."
    mock_respond.assert_called_once_with(expected_response_message)


@patch("src.app.logger")
def test_handle_gather_feedback_command_invalid_time_zero(mock_logger):
    """Test /gather-feedback with zero minutes."""
    mock_ack = MagicMock()
    mock_respond = MagicMock()
    mock_client = MagicMock()
    command_payload = {
        "user_id": "U_INVALID_TIME_ZERO",
        "text": "<!subteam^S1234567890|@test-group> in 0 minutes",
    }

    handle_gather_feedback_command(
        ack=mock_ack,
        command=command_payload,
        client=mock_client,
        logger=mock_logger,
        respond=mock_respond,
    )

    mock_ack.assert_called_once()
    mock_logger.warning.assert_called_once_with(
        "Invalid time '0' for /gather-feedback by user 'U_INVALID_TIME_ZERO'. Time must be a positive integer."
    )
    mock_respond.assert_called_once_with(
        "The time limit must be a positive number of minutes."
    )


@patch("src.app.logger")
def test_handle_gather_feedback_command_invalid_time_negative(mock_logger):
    """Test /gather-feedback with negative minutes."""
    mock_ack = MagicMock()
    mock_respond = MagicMock()
    mock_client = MagicMock()
    command_payload = {
        "user_id": "U_INVALID_TIME_NEG",
        "text": "<!subteam^S1234567890|@test-group> in -10 minutes",
    }

    handle_gather_feedback_command(
        ack=mock_ack,
        command=command_payload,
        client=mock_client,
        logger=mock_logger,
        respond=mock_respond,
    )

    mock_ack.assert_called_once()
    mock_logger.warning.assert_called_once_with(
        "Invalid time '-10' for /gather-feedback by user 'U_INVALID_TIME_NEG'. Time must be a positive integer."
    )
    mock_respond.assert_called_once_with(
        "The time limit must be a positive number of minutes."
    )


@patch("src.app.logger")
def test_handle_gather_feedback_command_general_exception(mock_logger):
    """Test general exception handling in /gather-feedback."""
    mock_ack = MagicMock()
    mock_respond = MagicMock()
    mock_client = MagicMock()
    command_payload = {
        "user_id": "U_EXCEPTION_USER",
        "text": "<!subteam^SOTHERGROUPID|@another-group>",
        "channel_id": "C_EXCEPTION_CHANNEL",
    }

    # Mock the usergroups_users_list to raise an exception *after* initial parsing and logging
    mock_client.usergroups_users_list.side_effect = Exception("Internal API error")

    handle_gather_feedback_command(
        ack=mock_ack,
        command=command_payload,
        client=mock_client,
        logger=mock_logger,
        respond=mock_respond,
    )

    mock_ack.assert_called_once()
    # Check that the generic error handler was invoked
    mock_logger.error.assert_called_once()
    args, kwargs = mock_logger.error.call_args
    assert (
        "Error handling /gather-feedback command for user 'U_EXCEPTION_USER'" in args[0]
    )
    assert "Internal API error" in str(
        args[0]
    )  # Check if the original exception message is part of the log
    assert kwargs.get("exc_info", False)

    mock_respond.assert_called_once_with(
        "Sorry, an unexpected error occurred while processing your request. Please try again."
    )


@patch("src.app.uuid.uuid4")
@patch("src.app.session_store")
@patch("src.app.logger")
@patch.dict(os.environ, {"DEFAULT_SESSION_MINUTES": "10"}, clear=True)
def test_handle_gather_feedback_command_default_time_env_var_set(
    mock_logger, mock_session_store, mock_uuid4
):
    """Test /gather-feedback uses DEFAULT_SESSION_MINUTES when no time is specified."""
    mock_ack = MagicMock()
    mock_respond = MagicMock()
    mock_client = MagicMock()
    mock_client.usergroups_users_list.return_value = {
        "users": ["U_MEMBER1", "U_MEMBER2"]
    }
    command_payload = {
        "text": "<!subteam^SGROUPID|@group>",
        "user_id": "U_INITIATOR",
        "channel_id": "C_CHANNEL",
        "command": "/gather-feedback",
    }
    session_id = "test-session-id-default-env"
    mock_uuid4.return_value = session_id

    handle_gather_feedback_command(
        ack=mock_ack,
        command=command_payload,
        client=mock_client,
        respond=mock_respond,
        logger=mock_logger,
    )

    mock_ack.assert_called_once()
    mock_client.usergroups_users_list.assert_called_once_with(usergroup="SGROUPID")

    assert mock_session_store.add_session.call_count == 1
    added_session = mock_session_store.add_session.call_args[0][0]
    assert isinstance(added_session, SessionData)
    assert added_session.session_id == session_id
    assert added_session.initiator_user_id == "U_INITIATOR"
    assert added_session.channel_id == "C_CHANNEL"
    assert added_session.target_user_ids == ["U_MEMBER1", "U_MEMBER2"]
    assert added_session.time_limit_minutes == 10

    mock_logger.info.assert_any_call(
        "Parsed for /gather-feedback from user 'U_INITIATOR': group_id='SGROUPID', handle='@group', time not specified, using default: 10 minutes"
    )
    mock_respond.assert_called_once_with(
        f"Okay, I've initiated a feedback session (ID: {session_id}) for @group (with 2 member(s)), for 10 minutes. I'll reach out to them shortly."
    )


@patch("src.app.uuid.uuid4")
@patch("src.app.session_store")
@patch("src.app.logger")
@patch.dict(os.environ, {}, clear=True)
def test_handle_gather_feedback_command_default_time_env_var_not_set(
    mock_logger, mock_session_store, mock_uuid4
):
    """Test /gather-feedback uses fallback default (5 mins) when no time and no env var."""
    mock_ack = MagicMock()
    mock_respond = MagicMock()
    mock_client = MagicMock()
    mock_client.usergroups_users_list.return_value = {"users": ["U_MEMBER1"]}
    command_payload = {
        "text": "<!subteam^SGROUPID2|@group2>",
        "user_id": "U_INITIATOR2",
        "channel_id": "C_CHANNEL2",
        "command": "/gather-feedback",
    }
    session_id = "test-session-id-default-no-env"
    mock_uuid4.return_value = session_id

    handle_gather_feedback_command(
        ack=mock_ack,
        command=command_payload,
        client=mock_client,
        respond=mock_respond,
        logger=mock_logger,
    )

    mock_ack.assert_called_once()
    assert mock_session_store.add_session.call_count == 1
    added_session = mock_session_store.add_session.call_args[0][0]
    assert added_session.time_limit_minutes == 5

    mock_logger.info.assert_any_call(
        "Parsed for /gather-feedback from user 'U_INITIATOR2': group_id='SGROUPID2', handle='@group2', time not specified, using default: 5 minutes"
    )
    mock_respond.assert_called_once_with(
        "Okay, I've initiated a feedback session (ID: test-session-id-default-no-env) for @group2 (with 1 member(s)), for 5 minutes. I'll reach out to them shortly."
    )


@patch("src.app.uuid.uuid4")
@patch("src.app.session_store")
@patch("src.app.logger")
@patch.dict(os.environ, {"DEFAULT_SESSION_MINUTES": "invalid_value"}, clear=True)
def test_handle_gather_feedback_command_default_time_env_var_invalid_format(
    mock_logger, mock_session_store, mock_uuid4
):
    """Test /gather-feedback uses fallback default (5 mins) when env var is invalid format."""
    mock_ack = MagicMock()
    mock_respond = MagicMock()
    mock_client = MagicMock()
    mock_client.usergroups_users_list.return_value = {"users": ["U_MEMBERX"]}
    command_payload = {
        "text": "<!subteam^SGROUPID3|@group3>",
        "user_id": "U_INITIATOR3",
        "channel_id": "C_CHANNEL3",
        "command": "/gather-feedback",
    }
    session_id = "test-session-id-default-invalid-env"
    mock_uuid4.return_value = session_id

    handle_gather_feedback_command(
        ack=mock_ack,
        command=command_payload,
        client=mock_client,
        respond=mock_respond,
        logger=mock_logger,
    )

    mock_ack.assert_called_once()
    assert mock_session_store.add_session.call_count == 1
    added_session = mock_session_store.add_session.call_args[0][0]
    assert added_session.time_limit_minutes == 5

    mock_logger.warning.assert_any_call(
        "Invalid DEFAULT_SESSION_MINUTES format 'invalid_value' (must be an integer), defaulting to 5 minutes."
    )
    mock_logger.info.assert_any_call(
        "Parsed for /gather-feedback from user 'U_INITIATOR3': group_id='SGROUPID3', handle='@group3', time not specified, using fallback default: 5 minutes"
    )
    mock_respond.assert_called_once_with(
        "Okay, I've initiated a feedback session (ID: test-session-id-default-invalid-env) for @group3 (with 1 member(s)), for 5 minutes. I'll reach out to them shortly."
    )


@patch("src.app.uuid.uuid4")
@patch("src.app.session_store")
@patch("src.app.logger")
@patch.dict(os.environ, {"DEFAULT_SESSION_MINUTES": "0"}, clear=True)
def test_handle_gather_feedback_command_default_time_env_var_non_positive(
    mock_logger, mock_session_store, mock_uuid4
):
    """Test /gather-feedback uses fallback default (5 mins) when env var is non-positive."""
    mock_ack = MagicMock()
    mock_respond = MagicMock()
    mock_client = MagicMock()
    mock_client.usergroups_users_list.return_value = {"users": ["U_MEMBERY"]}
    command_payload = {
        "text": "<!subteam^SGROUPID4|@group4>",
        "user_id": "U_INITIATOR4",
        "channel_id": "C_CHANNEL4",
        "command": "/gather-feedback",
    }
    session_id = "test-session-id-default-nonpos-env"
    mock_uuid4.return_value = session_id

    handle_gather_feedback_command(
        ack=mock_ack,
        command=command_payload,
        client=mock_client,
        respond=mock_respond,
        logger=mock_logger,
    )

    mock_ack.assert_called_once()
    assert mock_session_store.add_session.call_count == 1
    added_session = mock_session_store.add_session.call_args[0][0]
    assert added_session.time_limit_minutes == 5

    mock_logger.warning.assert_any_call(
        "Invalid DEFAULT_SESSION_MINUTES value '0' (must be positive), defaulting to 5 minutes."
    )
    mock_logger.info.assert_any_call(
        "Parsed for /gather-feedback from user 'U_INITIATOR4': group_id='SGROUPID4', handle='@group4', time not specified, using default: 5 minutes"
    )
    mock_respond.assert_called_once_with(
        "Okay, I've initiated a feedback session (ID: test-session-id-default-nonpos-env) for @group4 (with 1 member(s)), for 5 minutes. I'll reach out to them shortly."
    )


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

    # Assert open_feedback_modal was called after ack and uuid generation
    mock_open_feedback_modal.assert_called_once_with(
        client=mock_client,
        trigger_id=test_trigger_id,
        session_id=test_session_id,
    )
    mock_logger.info.assert_any_call(
        f"Attempted to open feedback modal with session_id '{test_session_id}' for user '{test_user_id}'."
    )

    # Check that session_store.add_session was called with a SessionData instance after modal open
    assert mock_session_store.add_session.call_count == 1
    added_session_arg = mock_session_store.add_session.call_args[0][0]
    assert isinstance(added_session_arg, SessionData)
    assert added_session_arg.session_id == test_session_id
    assert added_session_arg.initiator_user_id == test_user_id
    assert added_session_arg.channel_id == test_channel_id
    assert added_session_arg.target_user_ids == [test_user_id]
    assert added_session_arg.time_limit_minutes is None

    mock_logger.info.assert_any_call(
        f"Created and stored session '{test_session_id}' for user '{test_user_id}'."
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
        f"Unexpected error in /test-feedback for user '{test_user_id}': {test_exception}",
        exc_info=True,
    )
    mock_respond.assert_called_once_with(
        text="Sorry, an unexpected error occurred. Please try again."
    )
    mock_open_feedback_modal.assert_called_once_with(
        client=mock_client,
        trigger_id=test_trigger_id,
        session_id=str(mock_uuid4.return_value),
    )  # Should be called before session creation fails
