import datetime
import threading
from typing import Dict, Optional

from src.session_data import SessionData


class ThreadSafeSessionStore:
    """A thread-safe store for managing feedback sessions in memory."""

    def __init__(self):
        self._sessions: Dict[str, SessionData] = {}
        self._lock = threading.Lock()

    def add_session(self, session_data: SessionData) -> None:
        """
        Adds a new session to the store.
        Raises ValueError if a session with the same ID already exists.
        """
        with self._lock:
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
