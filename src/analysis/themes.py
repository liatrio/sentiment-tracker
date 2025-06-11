"""OpenAI-powered theme extraction utility."""
from __future__ import annotations

import json
import re
from typing import Any, List

from src.openai_client import chat_completion

# Regex to capture the first JSON array in the model response (robust to extra text)
_RESPONSE_RE = re.compile(r"\[[^\]]*\]")


def _parse_response(content: str) -> List[str]:
    """Return list of themes from the raw model *content* string."""

    match = _RESPONSE_RE.search(content)
    if not match:
        raise ValueError("Model response did not contain a JSON array")

    try:
        data: Any = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError("Failed to parse JSON from model response") from exc

    if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
        raise ValueError("JSON payload was not an array of strings")

    return data


_PROMPT_SYSTEM = (
    "You are an expert analyst. Given a set of feedback sentences, identify up "
    "to N overarching *themes* expressed. Respond ONLY with a minified JSON "
    'array of theme strings (e.g. ["communication", "work-life balance"]). '
    "Do not include any other keys or text. Themes must be short noun phrases."
)


def extract_themes(
    feedback: List[str], *, max_themes: int = 5, temperature: float = 0.0
) -> List[str]:
    """Extract up to *max_themes* themes from the list of feedback strings.

    Parameters
    ----------
    feedback
        Collection of feedback sentences.
    max_themes
        Maximum number of themes to return (default 5).
    temperature
        Sampling temperature for OpenAI call (default deterministic 0.0).
    """

    if not feedback:
        return []

    joined = "\n".join(f"- {line}" for line in feedback)
    user_prompt = (
        f"Please extract up to {max_themes} high-level themes from the following "
        "feedback list. Return ONLY a JSON array of strings.\n\nFeedback:\n" + joined
    )

    messages = [
        {"role": "system", "content": _PROMPT_SYSTEM},
        {"role": "user", "content": user_prompt},
    ]

    response = chat_completion(messages, temperature=temperature)
    content: str = response["choices"][0]["message"]["content"]
    return _parse_response(content)
