"""Utility helpers for Slack interactions."""
from __future__ import annotations

import logging
from typing import List

from slack_sdk.errors import SlackApiError
from slack_sdk.web import WebClient

logger = logging.getLogger(__name__)


def get_channel_members(client: WebClient, channel_id: str | None) -> List[str]:
    """Return the list of *active human* user IDs in ``channel_id``.

    The helper handles pagination of ``conversations.members`` and filters out
    bot or deactivated users via ``users.info``.

    Args:
        client: Slack WebClient instance authenticated with the required scopes
            (``conversations:read`` and ``users:read``).
        channel_id: The Slack channel ID to inspect.

    Returns:
        List of user IDs that are *not* bots and are *not* deleted.
    """

    # If channel_id is None or empty, return empty list early to avoid unnecessary API calls
    if not channel_id:
        logger.debug("get_channel_members called with empty channel_id; returning []")
        return []

    members: List[str] = []
    cursor: str | None = None

    # ------------------------------------------------------------------
    # Fetch members with cursor-based pagination
    # ------------------------------------------------------------------
    while True:
        try:
            resp = client.conversations_members(
                channel=channel_id,  # type: ignore[arg-type]
                limit=1000,
                cursor=cursor or "",
            )
        except SlackApiError as exc:
            logger.error("Failed to fetch members for %s: %s", channel_id, exc)
            raise

        members.extend(resp.get("members", []))
        cursor = resp.get("response_metadata", {}).get("next_cursor") or None
        if not cursor:
            break

    # ------------------------------------------------------------------
    # Filter bots/deactivated users
    # ------------------------------------------------------------------
    filtered: List[str] = []
    for uid in members:
        try:
            info = client.users_info(user=uid)
            user_data = info.get("user", {})
            if user_data.get("deleted") or user_data.get("is_bot"):
                continue
            filtered.append(uid)
        except SlackApiError as exc:
            # Non-fatal – skip user
            logger.warning(
                "users.info failed for %s: %s", uid, exc.response.get("error")
            )

    return filtered


def validate_time_input(
    time_str: str | None, logger: logging.Logger
) -> tuple[int, bool]:
    """Validate and determine time limit from user input or environment variable.

    Args:
        time_str: String representation of requested time in minutes, or None to use default.
        logger: Logger instance for error/warning output.

    Returns:
        A tuple containing (time_in_minutes, is_valid).
        - time_in_minutes: The validated time in minutes, or default if none provided.
        - is_valid: Boolean indicating if the time value is valid.
    """
    import os

    # If time is specified in command
    if time_str:
        try:
            time_in_minutes = int(time_str)
            if time_in_minutes <= 0:
                logger.warning(
                    f"Invalid time '{time_str}' provided. Time must be positive."
                )
                return time_in_minutes, False
            return time_in_minutes, True
        except ValueError:
            logger.warning(f"Invalid time format '{time_str}'.")
            return 0, False

    # No time specified, use default from environment
    default_session_minutes_str = os.environ.get("DEFAULT_SESSION_MINUTES", "5")
    try:
        time_in_minutes = int(default_session_minutes_str)
        if time_in_minutes <= 0:
            logger.error(
                f"Invalid DEFAULT_SESSION_MINUTES '{default_session_minutes_str}'. "
                f"Must be a positive integer. Falling back to 5."
            )
            time_in_minutes = 5
    except (ValueError, TypeError):
        logger.error(
            f"Invalid DEFAULT_SESSION_MINUTES '{default_session_minutes_str}'. "
            f"Falling back to 5 minutes."
        )
        time_in_minutes = 5

    return time_in_minutes, True
