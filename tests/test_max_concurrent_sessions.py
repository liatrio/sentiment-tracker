"""Tests for maximum concurrent session limiting logic."""
from __future__ import annotations

import importlib
import os
import unittest
from contextlib import contextmanager
from typing import Iterator

import src.app as app_module
from src.session_data import SessionData
from src.session_store import ThreadSafeSessionStore


@contextmanager
def _temp_env(key: str, value: str | None) -> Iterator[None]:
    """Temporarily set / unset an environment variable inside the context."""
    original = os.environ.get(key)
    if value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = value
    try:
        yield
    finally:
        if original is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original


class TestMaxConcurrentSessions(unittest.TestCase):
    """Unit tests for session limit enforcement."""

    def _make_session(self, idx: int) -> SessionData:
        return SessionData(
            session_id=f"s{idx}",
            initiator_user_id=f"u{idx}",
            channel_id=f"c{idx}",
            target_user_ids=[f"t{idx}"],
        )

    def test_add_session_limit_enforced(self):
        store = ThreadSafeSessionStore(max_sessions=2)
        store.add_session(self._make_session(1))
        store.add_session(self._make_session(2))
        with self.assertRaisesRegex(ValueError, "Maximum concurrent session limit"):
            store.add_session(self._make_session(3))
        self.assertEqual(store.count(), 2)

    def test_unlimited_when_none(self):
        store = ThreadSafeSessionStore()
        for i in range(100):
            store.add_session(self._make_session(i))
        self.assertEqual(store.count(), 100)

    def test_env_parsing_valid(self):
        with _temp_env("MAX_CONCURRENT_SESSIONS", "3"):
            importlib.reload(app_module)
            self.assertEqual(app_module._get_max_sessions_from_env(), 3)

    def test_env_parsing_invalid(self):
        with _temp_env("MAX_CONCURRENT_SESSIONS", "not-an-int"):
            importlib.reload(app_module)
            self.assertIsNone(app_module._get_max_sessions_from_env())
        with _temp_env("MAX_CONCURRENT_SESSIONS", "-5"):
            importlib.reload(app_module)
            self.assertIsNone(app_module._get_max_sessions_from_env())


if __name__ == "__main__":
    unittest.main()
