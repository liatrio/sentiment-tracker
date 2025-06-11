"""Tests for the _expire_feedback_session hook in app.py."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import src.app as app


@pytest.mark.parametrize("session_present", [True, False])
def test_expire_feedback_session(monkeypatch, session_present):
    """Ensure session is removed and DM is attempted only when session existed."""
    session_id = "test-sess-123"
    initiator = "UINITIATOR"

    # Mock session store
    mock_store = MagicMock()
    mock_store.remove_session.return_value = object() if session_present else None
    monkeypatch.setattr(app, "session_store", mock_store)

    # Mock Slack client
    mock_client = MagicMock()

    # Execute
    app._expire_feedback_session(session_id, initiator, mock_client)

    # Session should always attempt removal
    mock_store.remove_session.assert_called_once_with(session_id)

    if session_present:
        # A DM should be sent when session existed
        mock_client.chat_postMessage.assert_called_once()
    else:
        mock_client.chat_postMessage.assert_not_called()
