import datetime
import logging
import threading
from typing import Callable, Dict, Optional

from src.exceptions import AlreadySubmittedError
from src.reporting.aggregator import process_session
from src.session_data import SessionData


class ThreadSafeSessionStore:
    """A thread-safe store for managing feedback sessions in memory."""

    def __init__(self, max_sessions: Optional[int] = None):
        """Create a new :class:`ThreadSafeSessionStore`.

        Args:
            max_sessions: Optional maximum number of *concurrent* active
                sessions allowed.  :pydata:`None` (default) means unlimited.
        """
        self._sessions: Dict[str, SessionData] = {}
        self._lock = threading.Lock()
        # None == unlimited
        self._max_sessions = max_sessions if (max_sessions or 0) > 0 else None
        self._logger = logging.getLogger(__name__)

    def add_session(self, session_data: SessionData) -> None:
        """
        Adds a new session to the store.
        Raises ValueError if a session with the same ID already exists.
        """
        with self._lock:
            # Check global limit first so we fail fast under high load.
            if (
                self._max_sessions is not None
                and len(self._sessions) >= self._max_sessions
            ):
                raise ValueError(
                    "Maximum concurrent session limit reached. "
                    "Try again later or finish existing sessions."
                )

            if session_data.session_id in self._sessions:
                raise ValueError(
                    f"Session with ID {session_data.session_id} already exists."
                )
            self._sessions[session_data.session_id] = session_data

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Retrieves a session by its ID. Returns None if not found."""
        with self._lock:
            # Update last_accessed_at when a session is retrieved
            session = self._sessions.get(session_id)
            if session:
                session.last_accessed_at = datetime.datetime.now(datetime.timezone.utc)
            return session

    def update_session(self, session_data: SessionData) -> None:
        """
        Updates an existing session.
        The provided SessionData object replaces the existing one.
        Raises ValueError if the session ID is not found.
        The caller is responsible for ensuring the SessionData object is the one to keep.
        This method also updates the last_accessed_at timestamp of the session.
        """
        with self._lock:
            if session_data.session_id not in self._sessions:
                raise ValueError(
                    f"Session with ID {session_data.session_id} not found for update."
                )
            # Ensure last_accessed_at is updated on the object being stored
            session_data.last_accessed_at = datetime.datetime.now(datetime.timezone.utc)
            self._sessions[session_data.session_id] = session_data

    def modify_session(
        self,
        session_id: str,
        modifier: Callable[[SessionData], None],
    ) -> SessionData:
        """Atomically apply *modifier* to the session inside the lock.

        The *modifier* callback receives the current :class:`SessionData` instance and
        may mutate it in-place. The session's ``last_accessed_at`` timestamp is
        refreshed automatically.

        Args:
            session_id: ID of the session to modify.
            modifier: A callable that will be executed with the session as its only
                argument while the internal lock is held.

        Returns:
            The modified :class:`SessionData` instance for convenience.

        Raises:
            ValueError: If *session_id* does not exist in the store.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise ValueError(f"Session with ID {session_id} not found.")

            modifier(session)
            # Update last accessed timestamp after mutation
            session.last_accessed_at = datetime.datetime.now(datetime.timezone.utc)
            return session

    def remove_session(self, session_id: str) -> Optional[SessionData]:
        """Removes a session by its ID. Returns the removed session or None if not found."""
        with self._lock:
            return self._sessions.pop(session_id, None)

    def get_all_sessions(self) -> Dict[str, SessionData]:
        """Returns a shallow copy of all sessions currently in the store."""
        with self._lock:
            return dict(self._sessions)

    def count(self) -> int:
        """Returns the total number of active sessions."""
        with self._lock:
            return len(self._sessions)

    # ------------------------------------------------------------------
    # New lifecycle helpers
    # ------------------------------------------------------------------

    def submit_feedback(
        self, session_id: str, user_id: str, feedback_item: str
    ) -> None:
        """Record feedback for a participant and update session state atomically."""

        def _apply(session: SessionData) -> None:  # noqa: WPS430 – local helper
            session.submit(user_id, feedback_item)
            if session.is_complete:
                self._logger.info(
                    "session_done", extra={"session_id": session.session_id}
                )

        try:
            self.modify_session(session_id, _apply)
            self._logger.info(
                "feedback_received",
                extra={"session_id": session_id, "user_id": user_id},
            )
        except AlreadySubmittedError:
            raise
        except ValueError:
            raise

    def mark_done(self, session_id: str) -> None:
        """Set session as completed and remove it from store (idempotent)."""
        with self._lock:
            session = self._sessions.pop(session_id, None)
        if session is not None:
            session.complete_session("")  # store empty summary placeholder
            self._logger.info("session_done", extra={"session_id": session_id})

    def get_active_sessions(self) -> Dict[str, SessionData]:
        """Return copy of active sessions for diagnostics."""
        return self.get_all_sessions()

    # ------------------------------------------------------------------
    # Reporting helper
    # ------------------------------------------------------------------

    def process_feedback(self, session_id: str):
        """Return aggregated feedback for *session_id* using reporting pipeline.

        Raises
        ------
        ValueError
            If the session does not exist.
        """
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found for processing.")
        return process_session(session)
