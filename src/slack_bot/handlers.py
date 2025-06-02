import logging
from typing import Any, Dict

from slack_bolt import Ack
from slack_sdk.web import WebClient

from src.session_store import ThreadSafeSessionStore

logger = logging.getLogger(__name__)


def handle_sentiment_selection(
    ack: Ack,
    body: Dict[str, Any],
    client: WebClient,  # Added client for potential future use (e.g., updating modal)
    logger: logging.Logger,  # Standard Bolt logger
    session_store: ThreadSafeSessionStore,
) -> None:
    """
    Handles sentiment selection button clicks from the feedback modal.

    Args:
        ack: A function to acknowledge the Slack action request.
        body: The request body from Slack, containing action details.
        client: The Slack WebClient instance.
        logger: The logger instance for logging events.
        session_store: The thread-safe store for managing session data.
    """
    ack()  # Acknowledge the action immediately

    try:
        action = body["actions"][0]
        selected_sentiment = action["value"]
        session_id = body["view"]["private_metadata"]

        logger.info(
            f"Sentiment selection received: session_id='{session_id}', sentiment='{selected_sentiment}'"
        )

        session_data = session_store.get_session(session_id)

        if session_data:
            session_data.feedback_sentiment = selected_sentiment
            # session_store.update_session(session_data) # Not strictly necessary if object is mutable and updated in place
            logger.info(
                f"Updated session '{session_id}' with sentiment: '{selected_sentiment}'"
            )
        else:
            logger.warning(
                f"Session ID '{session_id}' was absent from the session store."
            )

    except KeyError as e:
        logger.error(f"Error accessing key in action body: {e}. Body: {body}")
    except IndexError as e:
        logger.error(f"Error accessing action in body: {e}. Body: {body}")
    except Exception as e:  # noqa: E713
        logger.error(
            f"Error processing sentiment selection for session '{session_id}': {e}",
            exc_info=True,
        )


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

        logger.info(
            f"Feedback modal submission received for session_id='{session_id}'. "
            f"Well: '{feedback_well}', Improve: '{feedback_improve}'"
        )

        session_data = session_store.get_session(session_id)

        if session_data:
            session_data.feedback_well = feedback_well
            session_data.feedback_improve = feedback_improve
            # session_store.update_session(session_data) # Not strictly necessary if mutable
            logger.info(
                f"Updated session '{session_id}' with feedback: "
                f"Well='{feedback_well}', Improve='{feedback_improve}'"
            )
        else:
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
