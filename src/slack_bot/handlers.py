import logging
from typing import Any, Dict

from slack_bolt import Ack
from slack_sdk.web import WebClient

from src.session_data import SessionData
from src.session_store import ThreadSafeSessionStore

logger = logging.getLogger(__name__)


def handle_feedback_modal_submission(
    ack: Ack,
    body: Dict[str, Any],  # Full request body, view is also passed separately
    client: WebClient,  # For potential follow-up actions
    view: Dict[str, Any],  # The view payload from the submission
    logger: logging.Logger,  # Standard Bolt logger
    session_store: ThreadSafeSessionStore,
) -> None:
    """
    Handles the submission of the feedback modal.

    Args:
        ack: A function to acknowledge the Slack view submission.
        body: The full request body from Slack.
        client: The Slack WebClient instance.
        view: The view payload from the submission.
        logger: The logger instance for logging events.
        session_store: The thread-safe store for managing session data.
    """
    # Acknowledge the submission. By default, this closes the modal.
    # For errors, use ack(response_action="errors", errors={...})
    ack()

    try:
        session_id = view["private_metadata"]
        state_values = view["state"]["values"]

        feedback_well = (
            state_values.get("feedback_question_well_block", {})
            .get("feedback_question_well_input", {})
            .get("value")
        )
        feedback_improve = (
            state_values.get("feedback_question_improve_block", {})
            .get("feedback_question_improve_input", {})
            .get("value")
        )

        selected_sentiment = (
            state_values.get("sentiment_input_block", {})
            .get("sentiment_dropdown_action", {})
            .get("selected_option", {})
            .get("value")
        )

        logger.info(
            f"Feedback modal submission received for session_id='{session_id}'. "
            f"Sentiment: '{selected_sentiment}', Well: '{feedback_well}', Improve: '{feedback_improve}'"
        )

        def _apply_feedback(session: SessionData) -> None:  # noqa: WPS430
            session.feedback_sentiment = selected_sentiment
            session.feedback_well = feedback_well
            session.feedback_improve = feedback_improve

        try:
            session_store.modify_session(session_id, _apply_feedback)
            logger.info(
                f"Updated session '{session_id}' with feedback: "
                f"Sentiment: '{selected_sentiment}', Well='{feedback_well}', Improve='{feedback_improve}'"
            )
        except ValueError:
            logger.warning(
                f"Session ID '{session_id}' was absent from the session store during modal submission."
            )

    except KeyError as e:
        logger.error(f"Error accessing key in view submission: {e}. View: {view}")
    except Exception as e:  # noqa: E713
        logger.error(
            f"Error processing feedback modal submission for session '{session_id}': {e}",
            exc_info=True,
        )
