"""Database operations using Supabase (Postgres via REST API)."""

from __future__ import annotations

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
    """List all evaluations, most recent first."""
    client = get_client()
    result = (
        client.table("evaluations")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


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
    """Get all classifications for an evaluation."""
    client = get_client()
    result = (
        client.table("classifications")
        .select("*")
        .eq("evaluation_id", evaluation_id)
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
