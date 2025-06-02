import logging
import unittest
from unittest.mock import MagicMock

from src.session_data import SessionData
from src.slack_bot.handlers import handle_feedback_modal_submission


class TestHandlers(unittest.TestCase):
    def setUp(self):
        """Set up common test resources."""
        self.mock_ack = MagicMock()
        self.mock_client = MagicMock()
        self.mock_logger = MagicMock(spec=logging.Logger)
        self.mock_session_store = MagicMock()
        self.session_id = "test_session_123"
        self.user_id = "U123ABC"
        self.channel_id = "C123DEF"

    # --- Tests for handle_feedback_modal_submission ---
    def test_handle_feedback_modal_submission_success(self):
        """Test successful handling of feedback modal submission."""
        mock_session = SessionData(
            session_id=self.session_id, user_id=self.user_id, channel_id=self.channel_id
        )
        self.mock_session_store.get_session.return_value = mock_session

        feedback_well_text = "Everything was great!"
        feedback_improve_text = "Maybe add more unicorns."

        selected_sentiment_value = "positive"
        view_data = {
            "private_metadata": self.session_id,
            "state": {
                "values": {
                    "sentiment_input_block": {
                        "sentiment_dropdown_action": {
                            "selected_option": {"value": selected_sentiment_value}
                        }
                    },
                    "feedback_question_well_block": {
                        "feedback_question_well_input": {"value": feedback_well_text}
                    },
                    "feedback_question_improve_block": {
                        "feedback_question_improve_input": {
                            "value": feedback_improve_text
                        }
                    },
                }
            },
        }
        body = {"user": {"id": self.user_id}}

        handle_feedback_modal_submission(
            ack=self.mock_ack,
            body=body,  # Pass the body
            client=self.mock_client,
            view=view_data,
            logger=self.mock_logger,
            session_store=self.mock_session_store,
        )

        self.mock_ack.assert_called_once_with()
        self.mock_session_store.get_session.assert_called_once_with(self.session_id)
        self.assertEqual(mock_session.feedback_sentiment, selected_sentiment_value)
        self.assertEqual(mock_session.feedback_well, feedback_well_text)
        self.assertEqual(mock_session.feedback_improve, feedback_improve_text)
        self.mock_logger.info.assert_any_call(
            f"Feedback modal submission received for session_id='{self.session_id}'. "
            f"Sentiment: '{selected_sentiment_value}', Well: '{feedback_well_text}', Improve: '{feedback_improve_text}'"
        )
        self.mock_logger.info.assert_any_call(
            f"Updated session '{self.session_id}' with feedback: "
            f"Sentiment: '{selected_sentiment_value}', Well='{feedback_well_text}', Improve='{feedback_improve_text}'"
        )

    def test_handle_feedback_modal_submission_session_not_found(self):
        """Test modal submission handling when session is not found."""
        self.mock_session_store.get_session.return_value = None

        view_data = {
            "private_metadata": self.session_id,
            "state": {
                "values": {
                    "sentiment_input_block": {
                        "sentiment_dropdown_action": {
                            "selected_option": {"value": "neutral"}  # Example value
                        }
                    },
                    "feedback_question_well_block": {
                        "feedback_question_well_input": {"value": "Well"}
                    },
                    "feedback_question_improve_block": {
                        "feedback_question_improve_input": {"value": "Improve"}
                    },
                }
            },
        }
        body = {"user": {"id": self.user_id}}

        handle_feedback_modal_submission(
            ack=self.mock_ack,
            body=body,
            client=self.mock_client,
            view=view_data,
            logger=self.mock_logger,
            session_store=self.mock_session_store,
        )

        self.mock_ack.assert_called_once_with()
        self.mock_session_store.get_session.assert_called_once_with(self.session_id)
        self.mock_logger.warning.assert_called_once_with(
            f"Session ID '{self.session_id}' was absent from the session store during modal submission."
        )

    def test_handle_feedback_modal_submission_exception_handling(self):
        """Test exception handling during feedback modal submission."""
        self.mock_session_store.get_session.side_effect = Exception("Submission error")

        view_data = {
            "private_metadata": self.session_id,
            "state": {
                "values": {
                    "sentiment_input_block": {
                        "sentiment_dropdown_action": {
                            "selected_option": {"value": "negative"}  # Example value
                        }
                    },
                    "feedback_question_well_block": {
                        "feedback_question_well_input": {"value": "Test well"}
                    },
                    "feedback_question_improve_block": {
                        "feedback_question_improve_input": {"value": "Test improve"}
                    },
                }
            },
        }
        body = {"user": {"id": self.user_id}}

        handle_feedback_modal_submission(
            ack=self.mock_ack,
            body=body,
            client=self.mock_client,
            view=view_data,
            logger=self.mock_logger,
            session_store=self.mock_session_store,
        )

        self.mock_ack.assert_called_once_with()
        self.mock_logger.error.assert_called_once_with(
            f"Error processing feedback modal submission for session '{self.session_id}': Submission error",
            exc_info=True,
        )


if __name__ == "__main__":
    unittest.main()
