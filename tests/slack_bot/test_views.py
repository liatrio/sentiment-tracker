import unittest
from unittest.mock import Mock, patch

from slack_sdk.errors import SlackApiError

from src.slack_bot.views import get_feedback_modal_view, open_feedback_modal


class TestViews(unittest.TestCase):
    def test_get_feedback_modal_view_structure(self):
        """
        Tests the structure of the feedback modal view.
        Ensures all required elements, block_ids, and action_ids are present.
        """
        test_session_id = "test_sid_123"
        modal_view = get_feedback_modal_view(session_id=test_session_id)

        expected_modal_structure = {
            "private_metadata": test_session_id,
            "type": "modal",
            "callback_id": "feedback_modal_callback",
            "title": {
                "type": "plain_text",
                "text": "Share Your Feedback",
                "emoji": True,
            },
            "submit": {"type": "plain_text", "text": "Submit", "emoji": True},
            "close": {"type": "plain_text", "text": "Cancel", "emoji": True},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Please share your anonymous feedback about the session. Your honest thoughts help us improve!",
                    },
                },
                {
                    "type": "actions",
                    "block_id": "sentiment_selection_block",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "😊 Positive",
                                "emoji": True,
                            },
                            "value": "positive",
                            "action_id": "sentiment_positive_button",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "😐 Neutral",
                                "emoji": True,
                            },
                            "value": "neutral",
                            "action_id": "sentiment_neutral_button",
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "😞 Negative",
                                "emoji": True,
                            },
                            "value": "negative",
                            "action_id": "sentiment_negative_button",
                        },
                    ],
                },
                {
                    "type": "input",
                    "block_id": "feedback_question_well_block",
                    "optional": False,
                    "label": {
                        "type": "plain_text",
                        "text": "What went well this session?",
                        "emoji": True,
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "feedback_question_well_input",
                        "multiline": True,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Examples: specific topics covered, pacing, interaction, tools used...",
                            "emoji": True,
                        },
                    },
                },
                {
                    "type": "input",
                    "block_id": "feedback_question_improve_block",
                    "optional": False,
                    "label": {
                        "type": "plain_text",
                        "text": "What could be improved for next time?",
                        "emoji": True,
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "feedback_question_improve_input",
                        "multiline": True,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Examples: areas to focus more on, suggestions for activities, technical issues...",
                            "emoji": True,
                        },
                    },
                },
            ],
        }

        # Perform a deep comparison of the two dictionaries
        self.assertDictEqual(modal_view, expected_modal_structure)

    @patch("src.slack_bot.views.get_feedback_modal_view")
    @patch("slack_sdk.web.WebClient")
    def test_open_feedback_modal_success(self, MockWebClient, mock_get_view):
        """Test that open_feedback_modal calls views_open with correct parameters on success."""
        mock_client_instance = MockWebClient.return_value
        mock_trigger_id = "test_trigger_id"
        mock_session_id = "session_success_456"
        expected_modal_view = {
            "type": "modal",
            "title": "Test Modal",
            "private_metadata": mock_session_id,
        }  # Simplified
        mock_get_view.return_value = expected_modal_view

        open_feedback_modal(
            client=mock_client_instance,
            trigger_id=mock_trigger_id,
            session_id=mock_session_id,
        )

        mock_get_view.assert_called_once_with(session_id=mock_session_id)
        mock_client_instance.views_open.assert_called_once_with(
            trigger_id=mock_trigger_id, view=expected_modal_view
        )

    @patch("src.slack_bot.views.logger")  # Patch logger to check error logging
    @patch("src.slack_bot.views.get_feedback_modal_view")
    @patch("slack_sdk.web.WebClient")
    def test_open_feedback_modal_slack_api_error(
        self, MockWebClient, mock_get_view, mock_logger
    ):
        """Test that open_feedback_modal logs an error when SlackApiError occurs."""
        mock_client_instance = MockWebClient.return_value
        mock_trigger_id = "test_trigger_id_api_error"
        mock_session_id = "session_api_error_789"
        expected_modal_view = {
            "type": "modal",
            "title": "Test Modal",
            "private_metadata": mock_session_id,
        }
        mock_get_view.return_value = expected_modal_view

        # Configure the mock client's views_open to raise SlackApiError
        mock_response = Mock()
        mock_response.data = {"ok": False, "error": "test_slack_api_error"}
        mock_client_instance.views_open.side_effect = SlackApiError(
            message="API call failed", response=mock_response
        )

        open_feedback_modal(
            client=mock_client_instance,
            trigger_id=mock_trigger_id,
            session_id=mock_session_id,
        )

        mock_get_view.assert_called_once_with(session_id=mock_session_id)
        mock_client_instance.views_open.assert_called_once_with(
            trigger_id=mock_trigger_id, view=expected_modal_view
        )
        mock_logger.error.assert_called_once_with(
            f"Error opening feedback modal for trigger_id {mock_trigger_id}: test_slack_api_error"
        )

    @patch("src.slack_bot.views.logger")  # Patch logger to check error logging
    @patch("src.slack_bot.views.get_feedback_modal_view")
    @patch("slack_sdk.web.WebClient")
    def test_open_feedback_modal_unexpected_error(
        self, MockWebClient, mock_get_view, mock_logger
    ):
        """Test that open_feedback_modal logs an error when an unexpected Exception occurs."""
        mock_client_instance = MockWebClient.return_value
        mock_trigger_id = "test_trigger_id_unexpected_error"
        mock_session_id = "session_unexpected_error_012"
        expected_modal_view = {
            "type": "modal",
            "title": "Test Modal",
            "private_metadata": mock_session_id,
        }
        mock_get_view.return_value = expected_modal_view

        # Configure the mock client's views_open to raise a generic Exception
        test_exception = Exception("Unexpected error!")
        mock_client_instance.views_open.side_effect = test_exception

        open_feedback_modal(
            client=mock_client_instance,
            trigger_id=mock_trigger_id,
            session_id=mock_session_id,
        )

        mock_get_view.assert_called_once_with(session_id=mock_session_id)
        mock_client_instance.views_open.assert_called_once_with(
            trigger_id=mock_trigger_id, view=expected_modal_view
        )
        mock_logger.error.assert_called_once_with(
            f"An unexpected error occurred while opening feedback modal for trigger_id {mock_trigger_id}: {test_exception}"
        )


if __name__ == "__main__":
    unittest.main()
