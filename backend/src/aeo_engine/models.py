"""Pydantic models for the AEO engine."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class PromptType(StrEnum):
    """Multi-dimension prompt classification."""

    DIRECT = "direct"
    COMPARATIVE = "comparative"
    USE_CASE = "use_case"
    FEATURE = "feature"
    NEGATIVE = "negative"


class Classification(StrEnum):
    """How a brand appears in a Gemini response."""

    DIRECT_WINNER = "direct_winner"
    ALTERNATIVE_MENTION = "alternative_mention"
    OMITTED = "omitted"


class PromptRecord(BaseModel):
    """A single prompt in the corpus."""

    id: str
    prompt_type: PromptType
    text: str
    inverted: bool = False  # True = brand order swapped (competitive symmetry)


class GeminiResponse(BaseModel):
    """Raw response from Gemini, stored verbatim."""

    id: str | None = None
    evaluation_id: str
    prompt_id: str
    run_index: int = Field(ge=1)
    model_id: str
    raw_text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ClassificationResult(BaseModel):
    """Classification of a single Gemini response for a brand."""

    response_id: str
    brand: str
    classification: Classification
    first_mention_position: int | None = None  # character offset
    mention_count: int = 0
    confidence_score: float = 0.0  # classifier's self-assessed confidence


class Evaluation(BaseModel):
    """A full evaluation run (N runs × M prompts)."""

    id: str | None = None
    brand: str
    category: str
    sampling_n: int
    status: str = "pending"  # pending | running | completed | failed
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class MetricSummary(BaseModel):
    """Aggregated metric for one prompt type × brand combination."""

    evaluation_id: str
    prompt_type: PromptType
    brand: str
    win_rate: float
    ci_lower: float  # confidence interval lower bound
    ci_upper: float  # confidence interval upper bound
    total_runs: int
    direct_wins: int
    alternative_mentions: int
    omitted: int


class DashboardData(BaseModel):
    """Full dashboard payload."""

    evaluation: Evaluation
    metrics: list[MetricSummary]
    responses: list[GeminiResponse]
    classifications: list[ClassificationResult]


class Competitor(BaseModel):
    """A competitor resolved by Gemini for a brand + category."""

    name: str
    reason: str
