"""Utility to generate a concise feedback summary using OpenAI."""
from __future__ import annotations

import logging
from typing import List

from src.openai_client import chat_completion

_logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a helpful assistant tasked with summarizing employee feedback. "
    "You have already anonymized quotes and extracted high-level themes. "
    "Write a concise summary (<=150 words, neutral tone) that highlights the "
    "overall sentiment, recurring themes, and key takeaways. Do not mention "
    "identities, quotes, or counts explicitly. Simply describe the gist."
)


def _build_user_prompt(quotes: List[str], themes: List[str]) -> str:
    theme_lines = (
        "\n".join(f"- {t}" for t in themes) if themes else "(no explicit themes)"
    )
    quotes_block = "\n".join(f'"{q}"' for q in quotes)
    return (
        "The high-level themes are:\n"
        f"{theme_lines}\n\n"
        "Here are anonymized quotes:\n"
        f"{quotes_block}\n\n"
        "Please produce the summary paragraph."
    )


def generate_summary(
    quotes: List[str],
    themes: List[str] | None = None,
    *,
    max_tokens: int = 250,
    temperature: float = 0.4,
    max_length_chars: int = 900,
) -> str:
    """Generate a concise textual summary of *quotes* guided by *themes*.

    Returns an empty string if *quotes* is empty.
    Raises RuntimeError after two failed attempts.
    """

    if not quotes:
        return ""

    themes = themes or []
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_prompt(quotes, themes)},
    ]

    attempts = 0
    while attempts < 2:
        attempts += 1
        try:
            resp = chat_completion(
                messages, temperature=temperature, max_tokens=max_tokens
            )
            content: str = resp["choices"][0]["message"]["content"].strip()
            if len(content) > max_length_chars:
                content = content[:max_length_chars].rstrip() + "…"
            return content
        except Exception as exc:  # noqa: BLE001
            _logger.warning("Summary generation attempt %d failed: %s", attempts, exc)
            if attempts >= 2:
                raise RuntimeError("OpenAI summary generation failed") from exc
    # Should never get here, but satisfy mypy
    return ""
