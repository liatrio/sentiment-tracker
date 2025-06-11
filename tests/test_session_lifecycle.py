"""Unit tests for session lifecycle management helpers."""

import pytest

from src.exceptions import AlreadySubmittedError
from src.session_data import SessionData
from src.session_store import ThreadSafeSessionStore


def test_session_submit_flow():
    """Ensure SessionData tracks pending/submitted users correctly."""
    session = SessionData(
        session_id="test-sess",
        initiator_user_id="UINIT",
        channel_id="C001",
        target_user_ids=["U1", "U2"],
        time_limit_minutes=10,
    )

    # Initial state
    assert session.pending_users == {"U1", "U2"}
    assert session.submitted_users == set()
    assert not session.is_complete

    # First submission
    session.submit("U1", "feedback 1")
    assert session.pending_users == {"U2"}
    assert session.submitted_users == {"U1"}
    assert not session.is_complete

    # Duplicate submission raises
    with pytest.raises(AlreadySubmittedError):
        session.submit("U1", "another feedback")

    # Unknown user raises
    with pytest.raises(ValueError):
        session.submit("UX", "bad")

    # Second submission completes session
    session.submit("U2", "feedback 2")
    assert session.is_complete
    assert session.pending_users == set()
    assert session.submitted_users == {"U1", "U2"}


def test_store_submit_and_mark_done():
    """ThreadSafeSessionStore helpers update sessions atomically."""
    store = ThreadSafeSessionStore()
    session = SessionData(
        session_id="sess-2",
        initiator_user_id="UINIT",
        channel_id="C001",
        target_user_ids=["U1"],
    )
    store.add_session(session)

    # Submit feedback via store
    store.submit_feedback("sess-2", "U1", "hi")
    stored = store.get_session("sess-2")
    assert stored is not None and stored.is_complete

    # Duplicate submission through store raises
    with pytest.raises(AlreadySubmittedError):
        store.submit_feedback("sess-2", "U1", "dup")

    # Invalid participant raises
    with pytest.raises(ValueError):
        store.submit_feedback("sess-2", "UX", "oops")

    # mark_done removes session and is idempotent
    store.mark_done("sess-2")
    assert store.get_session("sess-2") is None
    # second call no error
    store.mark_done("sess-2")
