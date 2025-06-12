"""Tests for regex parsing in process_gather_feedback_request."""
from __future__ import annotations

import os
from unittest.mock import ANY, MagicMock, patch

from src.app import process_gather_feedback_request
from src.session_data import SessionData


@patch("src.app.uuid.uuid4", return_value="sess-regex-1")
@patch("src.app.session_store")
@patch("src.app.logger")
def test_parse_group_and_reason(mock_logger, mock_session_store, mock_uuid4):
    """Command with user group *and* reason should populate SessionData.reason."""
    mock_client = MagicMock()
    mock_client.usergroups_users_list.return_value = {"users": ["U1", "U2"]}
    mock_respond = MagicMock()

    command_payload = {
        "text": "for <!subteam^SGRP01|@devs> on Quarterly planning",
        "user_id": "U_INIT",
        "channel_id": "C_MAIN",
    }

    # Ensure deterministic default time (5 min)
    with patch.dict(os.environ, {"DEFAULT_SESSION_MINUTES": "5"}, clear=False):
        process_gather_feedback_request(
            command=command_payload,
            client=mock_client,
            respond=mock_respond,
            logger=mock_logger,
        )

    mock_session_store.add_session.assert_called_once_with(ANY)
    session: SessionData = mock_session_store.add_session.call_args[0][0]
    assert session.reason == "Quarterly planning"
    # Default time used
    assert session.time_limit_minutes == 5


@patch("src.app.uuid.uuid4", return_value="sess-regex-2")
@patch("src.app.session_store")
@patch("src.app.logger")
def test_parse_group_reason_and_time(mock_logger, mock_session_store, mock_uuid4):
    """Command with group, reason and explicit time should parse correctly."""
    mock_client = MagicMock()
    mock_client.usergroups_users_list.return_value = {"users": ["U1"]}
    mock_respond = MagicMock()

    command_payload = {
        "text": "for <!subteam^SGRP02|@sales> on Sprint retro in 15 minutes",
        "user_id": "U_INIT",
        "channel_id": "C_MAIN",
    }

    process_gather_feedback_request(
        command=command_payload,
        client=mock_client,
        respond=mock_respond,
        logger=mock_logger,
    )

    mock_session_store.add_session.assert_called_once_with(ANY)
    session: SessionData = mock_session_store.add_session.call_args[0][0]
    assert session.reason == "Sprint retro"
    assert session.time_limit_minutes == 15
