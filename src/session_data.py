import datetime
from typing import List, Optional


class SessionData:
    """Represents the data associated with a single feedback session."""

    def __init__(
        self,
        session_id: str,
        initiator_user_id: str,  # User who started the session
        channel_id: str,  # Channel where the command was invoked or modal opened
        target_user_ids: List[str],  # List of users to collect feedback from
        time_limit_minutes: Optional[int] = None,  # Optional time limit in minutes
    ):
        """
        Initializes a new session.

        Args:
            session_id: The unique identifier for the session.
            initiator_user_id: The ID of the user who initiated the session.
            channel_id: The ID of the channel where the session was initiated.
            target_user_ids: A list of user IDs for whom feedback is being collected.
            time_limit_minutes: Optional duration in minutes for the feedback session.
        """
        self.session_id: str = session_id
        self.initiator_user_id: str = initiator_user_id
        self.channel_id: str = channel_id
        self.target_user_ids: List[str] = target_user_ids
        self.time_limit_minutes: Optional[int] = time_limit_minutes
        # For group sessions, feedback_items might need to be a Dict[str, List[str]]
        # mapping target_user_id to their feedback. For now, keeping it simple.
        self.feedback_items: List[str] = []  # Initialize as empty
        self.created_at: datetime.datetime = datetime.datetime.now(
            datetime.timezone.utc
        )
        self.last_accessed_at: datetime.datetime = self.created_at
        self.is_complete: bool = False
        self.anonymized_summary: Optional[str] = None
        # These individual feedback fields might be more relevant for single-user sessions
        # or aggregated reports. For group sessions, individual feedback per target_user_id
        # might be stored differently (e.g., in a dictionary).
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
            f"initiator_user_id='{self.initiator_user_id}'",
            f"target_user_ids={self.target_user_ids}",
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
