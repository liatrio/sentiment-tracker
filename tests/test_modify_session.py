import threading
import unittest
from typing import List

from src.session_data import SessionData
from src.session_store import ThreadSafeSessionStore


class TestModifySession(unittest.TestCase):
    """Unit tests for the modify_session helper."""

    def setUp(self) -> None:
        self.store = ThreadSafeSessionStore()
        self.session_id = "s1"
        self.store.add_session(
            SessionData(
                session_id=self.session_id,
                initiator_user_id="u1",
                channel_id="c1",
                target_user_ids=["t1"],
            )
        )

    def test_modify_updates_fields_atomically(self):
        def modifier(s: SessionData) -> None:
            s.feedback_sentiment = "positive"

        modified = self.store.modify_session(self.session_id, modifier)
        self.assertEqual(modified.feedback_sentiment, "positive")
        self.assertEqual(
            self.store.get_session(self.session_id).feedback_sentiment, "positive"
        )

    def test_modify_raises_for_missing_session(self):
        with self.assertRaises(ValueError):
            self.store.modify_session("missing", lambda s: None)

    def test_thread_safety_of_modify(self):
        num_threads = 20
        sentiments: List[str] = [f"sent_{i}" for i in range(num_threads)]

        def worker(idx: int) -> None:
            def mod(s: SessionData) -> None:
                s.feedback_sentiment = sentiments[idx]

            self.store.modify_session(self.session_id, mod)

        threads = [
            threading.Thread(target=worker, args=(i,)) for i in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        final = self.store.get_session(self.session_id)
        self.assertIn(final.feedback_sentiment, sentiments)


if __name__ == "__main__":
    unittest.main()
