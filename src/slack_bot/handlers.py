import logging
from typing import Any, Dict

from slack_bolt import Ack
from slack_sdk.web import WebClient

from src.session_data import SessionData
from src.session_store import ThreadSafeSessionStore

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Interaction handler: "Provide Feedback" button click
# ------------------------------------------------------------------


def handle_feedback_button_click(  # noqa: WPS211 – acceptable arg count for handler
    ack: Ack,
    body: Dict[str, Any],
    client: WebClient,
    logger: logging.Logger,
    session_store: ThreadSafeSessionStore,
) -> None:
    """Handle the `Provide Feedback` button click.

    This action is triggered when a participant clicks the button in the
    invitation DM.  The handler:

    1. Validates the *session_id* contained in the button ``value``.
    2. Prevents duplicate submissions by checking :pyattr:`SessionData.pending_users`.
    3. Opens (or re-opens) the feedback modal via
       :pyfunc:`src.slack_bot.views.open_feedback_modal`.
    4. Sends an *ephemeral* notice if the participant already submitted or the
       session is no longer active.
    """

    ack()  # acknowledge action early to avoid client timeouts

    try:
        user_id = body["user"]["id"]
        trigger_id = body["trigger_id"]

        # Slack transmits the Block Kit button's "value" string verbatim.
        action = body.get("actions", [{}])[0]
        payload_raw = action.get("value", "{}")
        try:
            import json as _json  # local import – avoid global unless needed

            payload = _json.loads(payload_raw)
            session_id = payload.get("session_id")
        except Exception:  # noqa: WPS424 – defensive parse
            session_id = None

        if not session_id:
            logger.warning("Button click missing session_id payload – body=%s", body)
            client.chat_postEphemeral(
                channel=body["channel"]["id"],
                user=user_id,
                text="Sorry, this feedback button is mis-configured.",
            )
            return

        session = session_store.get_session(session_id)
        if session is None:
            client.chat_postEphemeral(
                channel=body["channel"]["id"],
                user=user_id,
                text="This feedback session is no longer active.",
            )
            return

        if user_id not in session.pending_users:
            client.chat_postEphemeral(
                channel=body["channel"]["id"],
                user=user_id,
                text="You already submitted feedback for this session. Thanks!",
            )
            return

        # Everything looks good – open / re-open the modal
        from src.slack_bot.views import open_feedback_modal  # local to avoid cycles

        open_feedback_modal(client=client, trigger_id=trigger_id, session_id=session_id)

    except Exception as exc:  # pragma: no cover – catch-all to protect app thread
        logger.error("Error handling feedback button click: %s", exc, exc_info=True)


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

        user_id = body.get("user", {}).get("id")

        def _apply_feedback(session: SessionData) -> None:  # noqa: WPS430
            """Apply feedback and update session state atomically."""

            # Build feedback item string (could be structured later)
            feedback_item = (
                f"sentiment={selected_sentiment}, "
                f"well={feedback_well}, "
                f"improve={feedback_improve}"
            )

            try:
                # Uses SessionData.submit to update pending/submitted sets
                session.submit(user_id, feedback_item)
            except Exception:
                # Re-raise to outer scope
                raise

            # Store fields for richer reporting
            session.feedback_sentiment = selected_sentiment
            session.feedback_well = feedback_well
            session.feedback_improve = feedback_improve

        try:
            updated_session = session_store.modify_session(session_id, _apply_feedback)

            # Log successful update for observability / tests
            logger.info(
                f"Updated session '{session_id}' with feedback: "
                f"Sentiment: '{selected_sentiment}', Well='{feedback_well}', Improve='{feedback_improve}'"
            )

        except ValueError:
            # Session no longer exists – maybe GC'd or invalid ID
            logger.warning(
                f"Session ID '{session_id}' was absent from the session store during modal submission."
            )
            return

        # Notify initiator if session complete (only after successful update)
        if updated_session.is_complete:
            # ------------------------------------------------------------------
            # Aggregate feedback data now that collection is complete
            # ------------------------------------------------------------------
            try:
                processed = session_store.process_feedback(session_id)
                logger.info(
                    "Aggregated feedback for %s: sentiments=%s, stats=%s",
                    session_id,
                    processed.sentiment_counts,
                    processed.stats,
                )

                # Post full report to the original channel (or DM initiator)
                from src.reporting.render import post_report_to_slack  # local import

                post_report_to_slack(
                    processed=processed,
                    client=client,
                    channel=updated_session.channel_id,
                )
            except Exception as agg_exc:  # pragma: no cover – protect runtime
                logger.error("Aggregation failed for %s: %s", session_id, agg_exc)

            try:
                client.chat_postMessage(
                    channel=updated_session.initiator_user_id,
                    text=(
                        f"All participants have submitted feedback for session *{session_id}*. "
                        "Processing complete. You'll receive the report shortly!"
                    ),
                )
            except Exception as post_exc:  # noqa: WPS110
                logger.warning(
                    "Failed to notify initiator about completion of %s: %s",
                    session_id,
                    post_exc,
                )

    except KeyError as e:
        logger.error(f"Error accessing key in view submission: {e}. View: {view}")
    except Exception as e:  # noqa: E713
        logger.error(
            f"Error processing feedback modal submission for session '{session_id}': {e}",
            exc_info=True,
        )
