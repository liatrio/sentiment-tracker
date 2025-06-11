"""Unit tests for handle_feedback_button_click."""

from unittest.mock import MagicMock, patch

import pytest

from src.session_data import SessionData
from src.slack_bot.handlers import handle_feedback_button_click


@pytest.fixture()
def dummy_session():
    return SessionData(
        session_id="S123",
        initiator_user_id="U_INIT",
        channel_id="C123",
        target_user_ids=["U1", "U2"],
        time_limit_minutes=None,
    )


def _build_body(user_id="U1", session_id="S123"):
    return {
        "user": {"id": user_id},
        "trigger_id": "TRIGGER",
        "channel": {"id": "C_DM"},
        "actions": [
            {
                "value": f'{{"session_id": "{session_id}"}}',
            }
        ],
    }


@patch("src.slack_bot.views.open_feedback_modal")
def test_opens_modal_if_pending(mock_open_modal, dummy_session):
    ack = MagicMock()
    client = MagicMock()
    logger = MagicMock()
    store = MagicMock()
    store.get_session.return_value = dummy_session

    handle_feedback_button_click(
        ack=ack,
        body=_build_body("U1"),
        client=client,
        logger=logger,
        session_store=store,
    )

    mock_open_modal.assert_called_once_with(
        client=client, trigger_id="TRIGGER", session_id="S123"
    )
    client.chat_postEphemeral.assert_not_called()


@patch("src.slack_bot.views.open_feedback_modal")
def test_duplicate_submission_blocked(mock_open_modal, dummy_session):
    # Simulate U1 already submitted
    dummy_session.pending_users.remove("U1")
    dummy_session.submitted_users.add("U1")

    ack = MagicMock()
    client = MagicMock()
    logger = MagicMock()
    store = MagicMock()
    store.get_session.return_value = dummy_session

    handle_feedback_button_click(
        ack=ack,
        body=_build_body("U1"),
        client=client,
        logger=logger,
        session_store=store,
    )

    mock_open_modal.assert_not_called()
    client.chat_postEphemeral.assert_called_once()
    assert (
        "already submitted"
        in client.chat_postEphemeral.call_args.kwargs["text"].lower()
    )


@patch("src.slack_bot.views.open_feedback_modal")
def test_session_not_found(mock_open_modal):
    ack = MagicMock()
    client = MagicMock()
    logger = MagicMock()
    store = MagicMock()
    store.get_session.return_value = None

    handle_feedback_button_click(
        ack=ack,
        body=_build_body("U1", "MISSING"),
        client=client,
        logger=logger,
        session_store=store,
    )

    mock_open_modal.assert_not_called()
    client.chat_postEphemeral.assert_called_once()
    assert (
        "no longer active" in client.chat_postEphemeral.call_args.kwargs["text"].lower()
    )
