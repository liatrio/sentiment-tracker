"""Project-wide custom exception types."""


class AlreadySubmittedError(RuntimeError):
    """Raised when a participant attempts to submit feedback more than once."""

    def __init__(self, message: str) -> None:  # noqa: D401 – simple constructor
        super().__init__(message)
