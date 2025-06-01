import unittest
import threading
import time
import datetime

from src.session_data import SessionData
from src.session_store import ThreadSafeSessionStore

class TestSessionData(unittest.TestCase):
    def test_session_data_creation(self):
        session_id = "session123"
        user_id = "user456"
        channel_id = "channel789"
        initial_feedback = "Initial thought"
        
        session = SessionData(session_id, user_id, channel_id, initial_feedback)
        
        self.assertEqual(session.session_id, session_id)
        self.assertEqual(session.user_id, user_id)
        self.assertEqual(session.channel_id, channel_id)
        self.assertEqual(session.feedback_items, [initial_feedback])
        self.assertIsInstance(session.created_at, datetime.datetime)
        self.assertEqual(session.created_at.tzinfo, datetime.timezone.utc)
        self.assertEqual(session.created_at, session.last_accessed_at)
        self.assertFalse(session.is_complete)
        self.assertIsNone(session.anonymized_summary)

    def test_add_feedback(self):
        session = SessionData("s1", "u1", "c1")
        original_last_accessed = session.last_accessed_at
        # Ensure time changes, even a small delay might not be enough on fast systems
        # So we'll check for greater or equal and rely on the logic itself.
        # For robust testing, time could be mocked.
        time.sleep(0.001) 
        
        session.add_feedback("New feedback")
        self.assertEqual(session.feedback_items, ["New feedback"])
        self.assertGreaterEqual(session.last_accessed_at, original_last_accessed)
        self.assertTrue(session.last_accessed_at > original_last_accessed or session.last_accessed_at == original_last_accessed)


    def test_complete_session(self):
        session = SessionData("s1", "u1", "c1")
        original_last_accessed = session.last_accessed_at
        time.sleep(0.001) 
        
        summary = "This is the summary."
        session.complete_session(summary)
        
        self.assertTrue(session.is_complete)
        self.assertEqual(session.anonymized_summary, summary)
        self.assertGreaterEqual(session.last_accessed_at, original_last_accessed)


class TestThreadSafeSessionStore(unittest.TestCase):
    def setUp(self):
        self.store = ThreadSafeSessionStore()
        self.session_data1 = SessionData("s1", "u1", "c1", "feedback1")
        self.session_data2 = SessionData("s2", "u2", "c2", "feedback2")

    def test_add_and_get_session(self):
        self.store.add_session(self.session_data1)
        retrieved_session = self.store.get_session("s1")
        self.assertIsNotNone(retrieved_session)
        self.assertIs(retrieved_session, self.session_data1) # Should be the same object
        self.assertEqual(retrieved_session.session_id, "s1")
        self.assertEqual(self.store.count(), 1)

    def test_add_existing_session_raises_error(self):
        self.store.add_session(self.session_data1)
        session_data_same_id = SessionData("s1", "u_other", "c_other")
        with self.assertRaisesRegex(ValueError, "Session with ID s1 already exists."):
            self.store.add_session(session_data_same_id)

    def test_get_non_existent_session(self):
        retrieved_session = self.store.get_session("nonexistent")
        self.assertIsNone(retrieved_session)

    def test_get_session_updates_last_accessed(self):
        self.store.add_session(self.session_data1)
        original_last_accessed = self.session_data1.last_accessed_at
        time.sleep(0.001)
        self.store.get_session("s1")
        self.assertGreater(self.session_data1.last_accessed_at, original_last_accessed)

    def test_remove_session(self):
        self.store.add_session(self.session_data1)
        removed_session = self.store.remove_session("s1")
        self.assertIsNotNone(removed_session)
        self.assertIs(removed_session, self.session_data1)
        self.assertEqual(removed_session.session_id, "s1")
        self.assertIsNone(self.store.get_session("s1"))
        self.assertEqual(self.store.count(), 0)

    def test_remove_non_existent_session(self):
        removed_session = self.store.remove_session("nonexistent")
        self.assertIsNone(removed_session)

    def test_update_session(self):
        self.store.add_session(self.session_data1)
        original_creation_time = self.session_data1.created_at
        
        # Create a new object for update, as if it's a new state of the session
        updated_session_data = SessionData("s1", "u1_updated", "c1_updated", "feedback_updated")
        # Preserve creation time if that's the desired logic for an update
        updated_session_data.created_at = original_creation_time 
        # last_accessed_at will be set by update_session
        original_last_accessed = self.session_data1.last_accessed_at
        time.sleep(0.001)

        self.store.update_session(updated_session_data)
        retrieved_session = self.store.get_session("s1")
        
        self.assertIsNotNone(retrieved_session)
        self.assertIs(retrieved_session, updated_session_data) # Points to the new object
        self.assertEqual(retrieved_session.user_id, "u1_updated")
        self.assertEqual(retrieved_session.feedback_items, ["feedback_updated"])
        self.assertEqual(retrieved_session.created_at, original_creation_time)
        self.assertGreater(retrieved_session.last_accessed_at, original_last_accessed)

    def test_update_non_existent_session_raises_error(self):
        non_existent_session_data = SessionData("nonexistent", "u", "c")
        with self.assertRaisesRegex(ValueError, "Session with ID nonexistent not found for update."):
            self.store.update_session(non_existent_session_data)

    def test_get_all_sessions(self):
        self.store.add_session(self.session_data1)
        self.store.add_session(self.session_data2)
        all_sessions = self.store.get_all_sessions()
        self.assertEqual(len(all_sessions), 2)
        self.assertIn("s1", all_sessions)
        self.assertIn("s2", all_sessions)
        self.assertIs(all_sessions["s1"], self.session_data1)
        # Test that it's a shallow copy
        all_sessions["s1"] = None # Modify the copy
        self.assertIsNotNone(self.store.get_session("s1")) # Original store should be unaffected
        self.assertIs(self.store.get_session("s1"), self.session_data1)

    def test_thread_safety_concurrent_adds(self):
        num_threads = 10
        sessions_per_thread = 50 # Reduced for faster test execution
        threads = []

        def add_sessions_task(thread_id_val):
            for i in range(sessions_per_thread):
                session_id = f"session_t{thread_id_val}_{i}"
                # Pass actual values to SessionData constructor
                session_data = SessionData(session_id, f"user_t{thread_id_val}", f"channel_t{thread_id_val}")
                self.store.add_session(session_data)

        for i in range(num_threads):
            thread = threading.Thread(target=add_sessions_task, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        self.assertEqual(self.store.count(), num_threads * sessions_per_thread)

    def test_thread_safety_concurrent_mixed_ops(self):
        num_initial_sessions = 100 # Reduced
        initial_ids = [f"s_init_{i}" for i in range(num_initial_sessions)]
        for session_id in initial_ids:
            self.store.add_session(SessionData(session_id, "u_init", "c_init"))
        
        num_threads = 10
        ops_per_thread = 20 # Reduced
        threads = []

        def worker_task(thread_id_val):
            for i in range(ops_per_thread):
                idx = (thread_id_val * ops_per_thread + i)
                session_id_to_op = initial_ids[idx % num_initial_sessions]
                
                op_type = idx % 3
                try:
                    if op_type == 0: # Add (attempt, might fail if ID collision from test setup)
                        # To avoid collision, use unique IDs for adds in this mixed test
                        # Or, focus this test on update/remove/get of existing items
                        # For now, let's try to update
                        updated_data = SessionData(session_id_to_op, f"user_updated_t{thread_id_val}_{i}", "channel_updated")
                        self.store.update_session(updated_data)
                    elif op_type == 1: # Get
                        self.store.get_session(session_id_to_op)
                    else: # Remove
                        self.store.remove_session(session_id_to_op)
                except ValueError: # Expected for updates/removes on already removed items
                    pass
                except KeyError: # Should not happen with current get/remove logic (returns None)
                    self.fail(f"KeyError for {session_id_to_op}")

        for i in range(num_threads):
            thread = threading.Thread(target=worker_task, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        self.assertGreaterEqual(self.store.count(), 0)
        for session_id, session_data in self.store.get_all_sessions().items():
            self.assertIsInstance(session_data, SessionData)
            self.assertEqual(session_id, session_data.session_id)

if __name__ == '__main__':
    unittest.main()
