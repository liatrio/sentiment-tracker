import datetime
from typing import List, Optional


class SessionData:
    """Represents the data associated with a single feedback session."""

    def __init__(
        self, session_id: str, user_id: str, channel_id: str, initial_feedback: str = ""
    ):
        """
        Initializes a new session.

        Args:
            session_id: The unique identifier for the session.
            user_id: The ID of the user who initiated the session.
            channel_id: The ID of the channel where the session was initiated.
            initial_feedback: Optional initial feedback item to start the session.
        """
        self.session_id: str = session_id
        self.user_id: str = user_id
        self.channel_id: str = channel_id
        self.feedback_items: List[str] = [initial_feedback] if initial_feedback else []
        self.created_at: datetime.datetime = datetime.datetime.now(
            datetime.timezone.utc
        )
        self.last_accessed_at: datetime.datetime = self.created_at
        self.is_complete: bool = False
        self.anonymized_summary: Optional[str] = None
        self.feedback_sentiment: Optional[str] = None
        self.feedback_well: Optional[str] = None
        self.feedback_improve: Optional[str] = None

    def add_feedback(self, feedback_item: str) -> None:
        """Adds a new feedback item to the session and updates the last access time."""
        self.feedback_items.append(feedback_item)
        self.last_accessed_at = datetime.datetime.now(datetime.timezone.utc)

    def complete_session(self, anonymized_summary: str) -> None:
        """Marks the session as complete and stores the anonymized summary."""
        self.anonymized_summary = anonymized_summary
        self.is_complete = True
        self.last_accessed_at = datetime.datetime.now(datetime.timezone.utc)

    def __repr__(self) -> str:
        parts = [
            f"session_id='{self.session_id}'",
            f"user_id='{self.user_id}'",
            f"created_at='{self.created_at.isoformat()}'",
            f"feedback_count={len(self.feedback_items)}",
            f"is_complete={self.is_complete}",
        ]
        if self.feedback_sentiment:
            parts.append(f"feedback_sentiment='{self.feedback_sentiment}'")
        if self.feedback_well:
            parts.append(
                f"feedback_well='{self.feedback_well[:20]}...'"
                if len(self.feedback_well) > 20
                else f"feedback_well='{self.feedback_well}'"
            )
        if self.feedback_improve:
            parts.append(
                f"feedback_improve='{self.feedback_improve[:20]}...'"
                if len(self.feedback_improve) > 20
                else f"feedback_improve='{self.feedback_improve}'"
            )
        if self.anonymized_summary:
            parts.append(
                f"anonymized_summary='{self.anonymized_summary[:20]}...'"
                if len(self.anonymized_summary) > 20
                else f"anonymized_summary='{self.anonymized_summary}'"
            )
        return f"SessionData({', '.join(parts)})"
