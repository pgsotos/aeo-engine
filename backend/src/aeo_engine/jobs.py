"""Detecting evaluations whose background job died.

An evaluation's `status` records what the user asked for, not whether the
process doing it is still alive. `_execute_evaluation` runs in-process; if the
worker restarts — a deploy, an OOM, Render idling a free-tier service — the row
stays `running` forever, and the dashboard shows a job that will never finish.

The fix is a liveness signal, not a smarter status: the job touches
`heartbeat_at` as each prompt completes, and a row that has gone quiet for
longer than any prompt could reasonably take is declared dead.

The decision is a pure function so it can be tested without a database. The
caller applies it.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

# A full evaluation is 20 prompts under one semaphore and finishes in ~2
# minutes; a single prompt is seconds. Ten minutes is several times the worst
# realistic gap between heartbeats, so a live job is never mistaken for a dead
# one. Erring long only delays a row's transition to `failed` — erring short
# would kill a running evaluation.
STALE_AFTER = timedelta(minutes=10)


def _parse(value: Any) -> datetime | None:
    """Read a stored timestamp, or None when it cannot be read.

    Naive values are treated as UTC: `GeminiResponse.created_at` was written
    with a naive `utcnow()`, so both shapes exist in the table and comparing
    them directly would raise.
    """
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def stale_running_ids(evaluations: list[dict[str, Any]], now: datetime) -> list[str]:
    """Ids of `running` evaluations whose job has gone silent long enough to be dead.

    Only `running` rows are considered — a finished evaluation is never
    reopened. `heartbeat_at` is the signal; rows written before that column
    existed have none, so `created_at` stands in. A row whose timestamps cannot
    be parsed is left alone: an unreadable date is not evidence of death, and
    failing it would kill a live run on a parsing bug.
    """
    stale: list[str] = []
    for evaluation in evaluations:
        if evaluation.get("status") != "running":
            continue
        last_seen = _parse(evaluation.get("heartbeat_at")) or _parse(evaluation.get("created_at"))
        if last_seen is None:
            continue
        if now - last_seen > STALE_AFTER:
            stale.append(str(evaluation["id"]))
    return stale
