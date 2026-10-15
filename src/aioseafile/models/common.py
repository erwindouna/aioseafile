"""Shared helpers for the Seafile models."""

from datetime import UTC, datetime
from typing import Any


def from_timestamp(value: int) -> datetime:
    """Convert a Unix timestamp from Seafile to an aware datetime."""
    return datetime.fromtimestamp(value, tz=UTC)


def optional_datetime(value: str | None) -> datetime | None:
    """Parse an ISO timestamp that Seafile sends as an empty string when unset."""
    return datetime.fromisoformat(value) if value else None


def empty_to_none(value: Any) -> Any:
    """Map the empty string Seafile sends for unset values to None."""
    return None if value == "" else value


def optional_int(value: int | str | None) -> int | None:
    """Parse an ID that Seafile sends as an empty string when unset."""
    return None if value in (None, "") else int(value)
