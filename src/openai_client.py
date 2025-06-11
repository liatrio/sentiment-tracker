"""Lightweight OpenAI client helper.

Centralises API-key handling so the rest of the codebase can simply do:

    from src.openai_client import chat_completion

and know that the ``openai`` package is configured with credentials.
"""
from __future__ import annotations

import os
import types
from typing import Any, Dict, List


class OpenAIClientError(RuntimeError):
    """Raised when client configuration is invalid (e.g., missing API key)."""


_DEFAULT_MODEL = "gpt-4.1"


def _load_openai() -> types.ModuleType:
    """Import ``openai`` lazily.

    Loading is deferred so that unit tests can inject a stub into
    ``sys.modules`` before this function runs.
    """

    import importlib

    return importlib.import_module("openai")


def _ensure_api_key_present() -> str:
    """Return the ``OPENAI_API_KEY`` env var or raise.

    Raises
    ------
    OpenAIClientError
        If the env var is missing or empty.
    """

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise OpenAIClientError("OPENAI_API_KEY environment variable is not set.")
    return api_key


def get_openai_client() -> types.ModuleType:  # pragma: no cover – trivial
    """Configure and return the ``openai`` module.

    This sets ``openai.api_key`` and, if provided, ``openai.organization``.
    Subsequent calls reuse the configured module.
    """

    openai = _load_openai()

    if getattr(openai, "api_key", None):  # already configured
        return openai

    openai.api_key = _ensure_api_key_present()

    org = os.getenv("OPENAI_ORG")
    if org:
        openai.organization = org

    return openai


def chat_completion(
    messages: List[Dict[str, str]],
    *,
    model: str = _DEFAULT_MODEL,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Wrapper around ``openai.ChatCompletion.create`` with sane defaults.

    Parameters
    ----------
    messages
        Chat messages in OpenAI format.
    model
        Model id to use (default: ``gpt-4.1``).
    kwargs
        Additional parameters forwarded to ``ChatCompletion.create``.
    """

    openai = get_openai_client()

    return openai.ChatCompletion.create(model=model, messages=messages, **kwargs)
