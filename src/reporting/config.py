"""Configuration constants for the reporting pipeline."""
from __future__ import annotations

import os

# Maximum number of emojis displayed in the sentiment bar
MAX_EMOJI_BAR: int = int(os.getenv("REPORT_MAX_EMOJI_BAR", "20"))

# Maximum bullet points shown for each highlights section
MAX_BULLETS_EACH: int = int(os.getenv("REPORT_MAX_BULLETS_EACH", "5"))

# Maximum number of themes to list in the report
MAX_THEMES: int = int(os.getenv("REPORT_MAX_THEMES", "5"))

# Maximum anonymized comments to include verbatim (safety cap)
MAX_COMMENTS: int = int(os.getenv("REPORT_MAX_COMMENTS", "50"))

# Participation threshold (0–1) under which we flag low participation
LOW_PARTICIPATION_THRESHOLD: float = float(
    os.getenv("REPORT_LOW_PARTICIPATION_THRESHOLD", "0.5")
)
