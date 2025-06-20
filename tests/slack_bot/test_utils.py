"""Tests for slack_bot.utils helper functions."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.slack_bot.utils import get_channel_members


def _fake_user(is_bot: bool = False, deleted: bool = False):
    return {"user": {"id": "U", "is_bot": is_bot, "deleted": deleted}}


def test_get_channel_members_filters_and_paginates():
    client = MagicMock()

    # conversations.members returns two pages
    client.conversations_members.side_effect = [
        {
            "members": ["U1", "U2", "U3"],
            "response_metadata": {"next_cursor": "CUR"},
        },
        {"members": [], "response_metadata": {"next_cursor": ""}},
    ]

    # users.info responses per member
    def users_info_side_effect(user):  # noqa: D401 – simple helper
        mapping = {
            "U1": {"user": {"id": "U1", "is_bot": False, "deleted": False}},
            "U2": {"user": {"id": "U2", "is_bot": True, "deleted": False}},
            "U3": {"user": {"id": "U3", "is_bot": False, "deleted": True}},
        }
        return mapping[user]

    client.users_info.side_effect = users_info_side_effect

    out = get_channel_members(client, "C123")

    assert out == ["U1"]
    # pagination called twice
    assert client.conversations_members.call_count == 2
    # users_info called for each original member
    assert client.users_info.call_count == 3


def test_get_channel_members_propagates_error():
    client = MagicMock()
    from slack_sdk.errors import SlackApiError

    client.conversations_members.side_effect = SlackApiError(
        message="fail", response={"error": "unknown"}
    )

    with pytest.raises(SlackApiError):
        get_channel_members(client, "C123")
