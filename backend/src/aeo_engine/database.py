"""Database operations using Supabase (Postgres via REST API)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, cast

from supabase import Client, create_client

from aeo_engine.config import settings
from aeo_engine.models import (
    ClassificationResult,
    Evaluation,
    GeminiResponse,
    GroundingSource,
    GroundingSupport,
    MetricSummary,
)

_client: Client | None = None

Row = dict[str, Any]
"""One database row.

The Supabase client types `.execute().data` as an open JSON union, because a
REST payload could be anything. Every table in this project returns object
rows, so the three helpers below narrow that union once, at the boundary,
instead of scattering casts through the module. The cast is an assertion about
the schema, not a proof: if a query is changed to return a scalar, mypy will
not catch it — the schema in `migrations/` is the contract.
"""


def _rows(data: Any) -> list[Row]:
    """Narrow a multi-row `.data` payload."""
    return cast("list[Row]", data)


def _first_row(data: Any) -> Row:
    """Narrow the single-element list an insert or update returns."""
    return _rows(data)[0]


def _row_or_none(data: Any) -> Row | None:
    """Narrow a `.single()` payload, which is null when nothing matched."""
    return cast("Row | None", data)


_SETUP_HINT = """
Supabase is not configured. Set these in backend/.env (see .env.example):

  SUPABASE_URL=https://<your-project>.supabase.co
  SUPABASE_KEY=<anon public key>

Create a free project at https://supabase.com/dashboard, run
migrations/001_initial_schema.sql in its SQL Editor, then copy the Project URL
and the anon public key from Project Settings -> API.
"""


def get_client() -> Client:
    """Get or create the Supabase client (singleton).

    Raises with setup instructions when the credentials are missing, rather
    than letting the underlying client fail on an empty URL.
    """
    global _client
    if _client is None:
        missing = [
            name
            for name, value in (
                ("SUPABASE_URL", settings.supabase_url),
                ("SUPABASE_KEY", settings.supabase_key),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing {' and '.join(missing)}.\n{_SETUP_HINT}")
        _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client


# ── Evaluations ─────────────────────────────────────────────────────────────


def create_evaluation(evaluation: Evaluation) -> Row:
    """Insert a new evaluation record."""
    client = get_client()
    result = client.table("evaluations").insert(evaluation.model_dump(mode="json")).execute()
    return _first_row(result.data)


def get_evaluation(evaluation_id: str) -> Row | None:
    """Get an evaluation by ID, or None when no row matches.

    Uses `maybe_single()`, not `single()`: `single()` raises PGRST116 ("cannot
    coerce the result to a single JSON object") on an empty result, which made
    the `None` branch in the caller unreachable and turned an unknown ID into a
    500 instead of a 404.
    """
    client = get_client()
    result = (
        client.table("evaluations").select("*").eq("id", evaluation_id).maybe_single().execute()
    )
    return _row_or_none(result.data if result else None)


def update_evaluation(evaluation_id: str, updates: Row) -> Row:
    """Update an evaluation record."""
    client = get_client()
    result = client.table("evaluations").update(updates).eq("id", evaluation_id).execute()
    return _first_row(result.data)


def list_evaluations() -> list[Row]:
    """List all evaluations, most recent first, each with the brands it scored.

    The competitor set is not a column on `evaluations` — it is recovered from
    the metric rows, which carry one entry per brand. Each row gains a
    `competitors` list (the focus brand excluded, alphabetical); an evaluation
    still running has no metrics yet and gets an empty list.
    """
    client = get_client()
    evaluations = _rows(
        client.table("evaluations").select("*").order("created_at", desc=True).execute().data
    )
    if not evaluations:
        return []

    metric_rows = _rows(
        client.table("metrics")
        .select("evaluation_id,brand")
        .in_("evaluation_id", [e["id"] for e in evaluations])
        .execute()
        .data
    )

    brands_by_evaluation: dict[str, set[str]] = defaultdict(set)
    for row in metric_rows:
        brands_by_evaluation[row["evaluation_id"]].add(row["brand"])

    for evaluation in evaluations:
        scored = brands_by_evaluation.get(evaluation["id"], set())
        evaluation["competitors"] = sorted(scored - {evaluation["brand"]})

    return evaluations


# ── Gemini Responses ────────────────────────────────────────────────────────


def save_responses(responses: list[GeminiResponse]) -> list[Row]:
    """Batch insert Gemini responses (raw, immutable)."""
    if not responses:
        return []
    client = get_client()
    rows = [r.model_dump(mode="json") for r in responses]
    result = client.table("gemini_responses").insert(rows).execute()
    return _rows(result.data)


def get_responses(evaluation_id: str) -> list[Row]:
    """Get all responses for an evaluation."""
    client = get_client()
    result = (
        client.table("gemini_responses")
        .select("*")
        .eq("evaluation_id", evaluation_id)
        .order("prompt_id,run_index")
        .execute()
    )
    return _rows(result.data)


# ── Grounding ────────────────────────────────────────────────────────────────


def save_grounding_sources(
    response_id: str,
    sources: list[GroundingSource],
    supports: list[GroundingSupport],
) -> dict[str, list[Row]]:
    """Persist grounding sources and link support segments to them.

    Sources are inserted first (DB assigns ids); supports are then inserted
    with ``source_id`` resolved by matching ``source_chunk_index`` to the
    inserted source rows. A support whose chunk produced no source row (e.g.
    the chunk had no web title) persists with ``source_id=None`` — the segment
    offsets are preserved regardless. ``chunk_index`` is a linking aid only and
    is never persisted.
    """
    inserted_sources: list[Row] = []
    inserted_supports: list[Row] = []

    if sources:
        client = get_client()
        rows = [
            {
                "response_id": response_id,
                "web_title": s.web_title,
                "domain": s.domain,
            }
            for s in sources
        ]
        inserted_sources = _rows(client.table("grounding_sources").insert(rows).execute().data)

        if supports:
            chunk_to_id = {
                source.chunk_index: row["id"]
                for source, row in zip(sources, inserted_sources, strict=True)
            }
            support_rows = [
                {
                    "response_id": response_id,
                    "source_id": (
                        chunk_to_id.get(support.source_chunk_index)
                        if support.source_chunk_index is not None
                        else None
                    ),
                    "segment_start": support.segment_start,
                    "segment_end": support.segment_end,
                }
                for support in supports
            ]
            inserted_supports = _rows(
                client.table("grounding_supports").insert(support_rows).execute().data
            )

    return {"sources": inserted_sources, "supports": inserted_supports}


def get_grounding_sources(response_id: str) -> list[Row]:
    """Get all grounding sources for a response."""
    client = get_client()
    result = (
        client.table("grounding_sources")
        .select("*")
        .eq("response_id", response_id)
        .order("created_at")
        .execute()
    )
    return _rows(result.data)


def get_grounding_supports(response_id: str) -> list[Row]:
    """Get all grounding supports for a response."""
    client = get_client()
    result = (
        client.table("grounding_supports")
        .select("*")
        .eq("response_id", response_id)
        .order("segment_start")
        .execute()
    )
    return _rows(result.data)


def get_grounding_sources_for_evaluation(evaluation_id: str) -> list[Row]:
    """Get all grounding sources for an evaluation.

    Grounding sources don't have evaluation_id directly — join through
    gemini_responses to filter by evaluation_id (mirrors get_classifications).
    """
    client = get_client()

    resp_result = (
        client.table("gemini_responses").select("id").eq("evaluation_id", evaluation_id).execute()
    )
    response_ids = [r["id"] for r in _rows(resp_result.data)]
    if not response_ids:
        return []

    result = (
        client.table("grounding_sources")
        .select("*")
        .in_("response_id", response_ids)
        .order("created_at")
        .execute()
    )
    return _rows(result.data)


# ── Classifications ─────────────────────────────────────────────────────────


def save_classifications(classifications: list[ClassificationResult]) -> list[Row]:
    """Batch insert classification results."""
    if not classifications:
        return []
    client = get_client()
    rows = [c.model_dump(mode="json") for c in classifications]
    result = client.table("classifications").insert(rows).execute()
    return _rows(result.data)


def get_classifications(evaluation_id: str) -> list[Row]:
    """Get all classifications for an evaluation.

    Classifications don't have evaluation_id directly — join through
    gemini_responses to filter by evaluation_id.
    """
    client = get_client()

    # First get all response IDs for this evaluation
    resp_result = (
        client.table("gemini_responses").select("id").eq("evaluation_id", evaluation_id).execute()
    )
    response_ids = [r["id"] for r in _rows(resp_result.data)]
    if not response_ids:
        return []

    # Then get classifications for those responses
    result = client.table("classifications").select("*").in_("response_id", response_ids).execute()
    return _rows(result.data)


# ── Metrics ─────────────────────────────────────────────────────────────────


def save_metrics(metrics: list[MetricSummary]) -> list[Row]:
    """Batch insert computed metrics."""
    if not metrics:
        return []
    client = get_client()
    rows = [m.model_dump(mode="json") for m in metrics]
    result = client.table("metrics").insert(rows).execute()
    return _rows(result.data)


def get_metrics(evaluation_id: str) -> list[Row]:
    """Get all metrics for an evaluation."""
    client = get_client()
    result = client.table("metrics").select("*").eq("evaluation_id", evaluation_id).execute()
    return _rows(result.data)
