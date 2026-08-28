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
    MetricSummary,
)

_client: Client | None = None


def get_client() -> Client:
    """Get or create the Supabase client (singleton)."""
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client


# ── Evaluations ─────────────────────────────────────────────────────────────


def create_evaluation(evaluation: Evaluation) -> dict:
    """Insert a new evaluation record."""
    client = get_client()
    result = (
        client.table("evaluations")
        .insert(evaluation.model_dump(mode="json"))
        .execute()
    )
    return result.data[0]


def get_evaluation(evaluation_id: str) -> dict | None:
    """Get an evaluation by ID."""
    client = get_client()
    result = (
        client.table("evaluations")
        .select("*")
        .eq("id", evaluation_id)
        .single()
        .execute()
    )
    return result.data


def update_evaluation(evaluation_id: str, updates: dict) -> dict:
    """Update an evaluation record."""
    client = get_client()
    result = (
        client.table("evaluations")
        .update(updates)
        .eq("id", evaluation_id)
        .execute()
    )
    return result.data[0]


def list_evaluations() -> list[dict]:
    """List all evaluations, most recent first, each with the brands it scored.

    The competitor set is not a column on `evaluations` — it is recovered from
    the metric rows, which carry one entry per brand. Each row gains a
    `competitors` list (the focus brand excluded, alphabetical); an evaluation
    still running has no metrics yet and gets an empty list.
    """
    client = get_client()
    # The Supabase client types `.data` as untyped JSON; these are row dicts.
    evaluations = cast(
        "list[dict[str, Any]]",
        (
            client.table("evaluations")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        ).data,
    )
    if not evaluations:
        return []

    metric_rows = cast(
        "list[dict[str, Any]]",
        (
            client.table("metrics")
            .select("evaluation_id,brand")
            .in_("evaluation_id", [e["id"] for e in evaluations])
            .execute()
        ).data,
    )

    brands_by_evaluation: dict[str, set[str]] = defaultdict(set)
    for row in metric_rows:
        brands_by_evaluation[row["evaluation_id"]].add(row["brand"])

    for evaluation in evaluations:
        scored = brands_by_evaluation.get(evaluation["id"], set())
        evaluation["competitors"] = sorted(scored - {evaluation["brand"]})

    return evaluations


# ── Gemini Responses ────────────────────────────────────────────────────────


def save_responses(responses: list[GeminiResponse]) -> list[dict]:
    """Batch insert Gemini responses (raw, immutable)."""
    if not responses:
        return []
    client = get_client()
    rows = [r.model_dump(mode="json") for r in responses]
    result = client.table("gemini_responses").insert(rows).execute()
    return result.data


def get_responses(evaluation_id: str) -> list[dict]:
    """Get all responses for an evaluation."""
    client = get_client()
    result = (
        client.table("gemini_responses")
        .select("*")
        .eq("evaluation_id", evaluation_id)
        .order("prompt_id,run_index")
        .execute()
    )
    return result.data


# ── Classifications ─────────────────────────────────────────────────────────


def save_classifications(classifications: list[ClassificationResult]) -> list[dict]:
    """Batch insert classification results."""
    if not classifications:
        return []
    client = get_client()
    rows = [c.model_dump(mode="json") for c in classifications]
    result = client.table("classifications").insert(rows).execute()
    return result.data


def get_classifications(evaluation_id: str) -> list[dict]:
    """Get all classifications for an evaluation.

    Classifications don't have evaluation_id directly — join through
    gemini_responses to filter by evaluation_id.
    """
    client = get_client()

    # First get all response IDs for this evaluation
    resp_result = (
        client.table("gemini_responses")
        .select("id")
        .eq("evaluation_id", evaluation_id)
        .execute()
    )
    response_ids = [r["id"] for r in resp_result.data]
    if not response_ids:
        return []

    # Then get classifications for those responses
    result = (
        client.table("classifications")
        .select("*")
        .in_("response_id", response_ids)
        .execute()
    )
    return result.data


# ── Metrics ─────────────────────────────────────────────────────────────────


def save_metrics(metrics: list[MetricSummary]) -> list[dict]:
    """Batch insert computed metrics."""
    if not metrics:
        return []
    client = get_client()
    rows = [m.model_dump(mode="json") for m in metrics]
    result = client.table("metrics").insert(rows).execute()
    return result.data


def get_metrics(evaluation_id: str) -> list[dict]:
    """Get all metrics for an evaluation."""
    client = get_client()
    result = (
        client.table("metrics")
        .select("*")
        .eq("evaluation_id", evaluation_id)
        .execute()
    )
    return result.data
