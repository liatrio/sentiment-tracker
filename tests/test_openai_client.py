"""Tests for the OpenAI client helper."""
from __future__ import annotations

import importlib
import sys
from types import ModuleType

import pytest

# Module under test – will be imported lazily inside tests after env setup


class DummyChatCompletion:  # pragma: no cover – simple stub
    """Minimal stub mimicking openai.ChatCompletion class."""

    @staticmethod
    def create(**kwargs):  # noqa: D401,WPS110 – simple stub
        """Return the payload we received for assertion purposes."""
        return {"called_with": kwargs}


def _install_openai_stub(monkeypatch):
    """Insert a fake ``openai`` module into ``sys.modules``."""

    fake_openai = ModuleType("openai")
    fake_openai.ChatCompletion = DummyChatCompletion  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    return fake_openai


def reload_client_module():
    """Ensure a fresh import state for openai_client module."""

    if "src.openai_client" in sys.modules:
        del sys.modules["src.openai_client"]
    return importlib.import_module("src.openai_client")


def test_missing_api_key_raises(monkeypatch):
    """get_openai_client should raise if OPENAI_API_KEY is not set."""

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    _install_openai_stub(monkeypatch)

    oc = reload_client_module()

    with pytest.raises(oc.OpenAIClientError):
        oc.get_openai_client()


def test_successful_client(monkeypatch):
    """get_openai_client returns configured stub when key present."""

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    fake_openai = _install_openai_stub(monkeypatch)

    oc = reload_client_module()
    client = oc.get_openai_client()

    # Should be our stub module, and api_key attr set.
    assert client is fake_openai
    assert client.api_key == "test-key"


def test_chat_completion_wrapper(monkeypatch):
    """chat_completion should call underlying ChatCompletion.create."""

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    _install_openai_stub(monkeypatch)

    oc = reload_client_module()

    result = oc.chat_completion(
        [{"role": "user", "content": "Hello"}],
        temperature=0,
    )

    assert result["called_with"]["model"] == "gpt-4.1"
    assert result["called_with"]["messages"][0]["content"] == "Hello"
    assert result["called_with"]["temperature"] == 0
