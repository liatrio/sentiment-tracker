import json
import logging
from typing import Any, Dict, List, Optional

from slack_sdk.errors import SlackApiError
from slack_sdk.models.blocks import ActionsBlock, ButtonElement, SectionBlock
from slack_sdk.web import WebClient

logger = logging.getLogger(__name__)


def get_feedback_modal_view(
    session_id: str, *, reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    Constructs and returns the Block Kit JSON for the feedback modal.

    Args:
        session_id: The unique ID of the session to associate with this modal.
        reason: The reason for the feedback (optional).

    The modal includes:
    - A title "Share Your Feedback".
    - A callback_id "feedback_modal_callback".
    - A private_metadata field containing the session_id.
    - An introductory section.
    - An actions block for sentiment selection (Positive, Neutral, Negative).
    - Two input blocks for open-ended feedback questions.
    """
    blocks: List[Dict[str, Any]] = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Please share your anonymous feedback. "
                "Your honest thoughts help us improve!",
            },
        }
    ]

    # If a reason is provided, show it to give context
    if reason:
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Feedback on: {reason}*",
                    }
                ],
            }
        )

    # Existing sentiment + input blocks
    blocks.extend(
        [
            {
                "type": "input",
                "block_id": "sentiment_input_block",
                "label": {
                    "type": "plain_text",
                    "text": "Overall Sentiment",
                    "emoji": True,
                },
                "element": {
                    "type": "static_select",
                    "action_id": "sentiment_dropdown_action",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select a sentiment",
                        "emoji": True,
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "😊 Positive",
                                "emoji": True,
                            },
                            "value": "positive",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "😐 Neutral",
                                "emoji": True,
                            },
                            "value": "neutral",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "😞 Negative",
                                "emoji": True,
                            },
                            "value": "negative",
                        },
                    ],
                },
                "optional": False,
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
        ]
    )

    return {
        "type": "modal",
        "callback_id": "feedback_modal_callback",
        "private_metadata": session_id,
        "title": {"type": "plain_text", "text": "Share Your Feedback", "emoji": True},
        "submit": {"type": "plain_text", "text": "Submit", "emoji": True},
        "close": {"type": "plain_text", "text": "Cancel", "emoji": True},
        "blocks": blocks,
    }


def build_invitation_message(
    session_id: str,
    initiator_user_id: str,
    channel_id: Optional[str] = None,
    *,
    reason: Optional[str] = None,
) -> List[dict]:  # noqa: D401 – simple helper
    """Return Block Kit invitation message.

    Includes initiator and originating channel reference.
    """
    button = ButtonElement(
        text={"type": "plain_text", "text": "Provide Feedback"},
        action_id="open_feedback_modal",
        value=json.dumps({"session_id": session_id}),
        style="primary",
    )
    channel_ref = f" in <#{channel_id}>" if channel_id else ""
    reason_line = f"on *{reason}*" if reason else ""
    intro_text = (
        f":small-batch-and-fast-feedback: *Hi, from `sentiment-bot`* :small-batch-and-fast-feedback:\n\n"  # noqa: E231
        f"<@{initiator_user_id}> has requested your feedback {reason_line}\n"
        f"Watch {channel_ref} for the report.\n"
    )
    blocks = [
        SectionBlock(text={"type": "mrkdwn", "text": intro_text}),
        ActionsBlock(elements=[button]),
    ]
    return [block.to_dict() for block in blocks]


def open_feedback_modal(
    client: WebClient,
    trigger_id: str,
    session_id: str,
    *,
    reason: Optional[str] = None,
) -> None:
    """Opens the feedback modal in Slack.

    Args:
        client: The Slack WebClient instance.
        trigger_id: The trigger ID from the Slack interaction.
        session_id: The unique ID of the session to associate with this modal.
        reason: The reason for the feedback (optional).
    """
    try:
        if reason is not None:
            modal_view = get_feedback_modal_view(session_id=session_id, reason=reason)
        else:
            modal_view = get_feedback_modal_view(session_id=session_id)
        client.views_open(trigger_id=trigger_id, view=modal_view)
        logger.info(f"Successfully opened feedback modal for trigger_id: {trigger_id}")
    except SlackApiError as e:
        logger.error(
            f"Error opening feedback modal for trigger_id {trigger_id}: {e.response.data['error']}"
        )
        # Depending on requirements, you might re-raise or handle differently
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while opening feedback modal for trigger_id {trigger_id}: {e}"
        )
        # Handle unexpected errors
