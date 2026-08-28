"""Tests for stale-evaluation detection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from aeo_engine.jobs import STALE_AFTER, stale_running_ids

NOW = datetime(2026, 8, 28, 12, 0, 0, tzinfo=UTC)


def _row(
    id: str = "e1",
    status: str = "running",
    created_at: datetime | None = None,
    heartbeat_at: datetime | None = None,
) -> dict[str, object]:
    row: dict[str, object] = {
        "id": id,
        "status": status,
        "created_at": (created_at or NOW).isoformat(),
    }
    row["heartbeat_at"] = heartbeat_at.isoformat() if heartbeat_at else None
    return row


def test_fresh_heartbeat_is_not_stale() -> None:
    rows = [_row(heartbeat_at=NOW - timedelta(seconds=30))]
    assert stale_running_ids(rows, now=NOW) == []


def test_silent_past_the_threshold_is_stale() -> None:
    rows = [_row(heartbeat_at=NOW - STALE_AFTER - timedelta(seconds=1))]
    assert stale_running_ids(rows, now=NOW) == ["e1"]


def test_exactly_at_the_threshold_is_not_stale() -> None:
    """The boundary is exclusive: a job silent for exactly the grace period
    may still be mid-write. Only past it is it declared dead."""
    rows = [_row(heartbeat_at=NOW - STALE_AFTER)]
    assert stale_running_ids(rows, now=NOW) == []


def test_missing_heartbeat_falls_back_to_created_at() -> None:
    """Rows written before the heartbeat column existed have none. Their
    creation time is the only signal available, so it stands in."""
    fresh = _row(id="fresh", created_at=NOW - timedelta(minutes=1))
    dead = _row(id="dead", created_at=NOW - STALE_AFTER - timedelta(minutes=1))
    assert stale_running_ids([fresh, dead], now=NOW) == ["dead"]


def test_only_running_rows_are_swept() -> None:
    """A finished evaluation is never reopened, however old it is."""
    old = NOW - STALE_AFTER - timedelta(hours=5)
    rows = [
        _row(id="done", status="completed", heartbeat_at=old),
        _row(id="failed", status="failed", heartbeat_at=old),
        _row(id="pending", status="pending", heartbeat_at=old),
        _row(id="alive", status="running", heartbeat_at=old),
    ]
    assert stale_running_ids(rows, now=NOW) == ["alive"]


def test_naive_timestamps_are_read_as_utc() -> None:
    """GeminiResponse.created_at was written with a naive utcnow(), so some
    stored timestamps carry no offset. Treating them as UTC keeps the
    comparison from raising on aware/naive mixing."""
    naive = (NOW - STALE_AFTER - timedelta(minutes=1)).replace(tzinfo=None)
    rows = [
        {"id": "e1", "status": "running", "created_at": naive.isoformat(), "heartbeat_at": None}
    ]
    assert stale_running_ids(rows, now=NOW) == ["e1"]


def test_unparseable_timestamp_is_left_alone() -> None:
    """A row whose timestamps cannot be read is not evidence of death.
    Failing them would destroy a live run on a parsing bug."""
    rows = [{"id": "e1", "status": "running", "created_at": "not-a-date", "heartbeat_at": None}]
    assert stale_running_ids(rows, now=NOW) == []


def test_empty_input() -> None:
    assert stale_running_ids([], now=NOW) == []
