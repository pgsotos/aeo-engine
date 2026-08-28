"""Pydantic models for the AEO engine."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

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
    grounding_metadata: dict[str, Any] | None = (
        None  # Google Search grounding; None when absent (stochastic)
    )
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
    consistency: float | None = None  # 1 - pstdev over per-type DWR; None if <2 types
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class MetricSummary(BaseModel):
    """Aggregated metric for one prompt type × brand combination."""

    evaluation_id: str
    prompt_type: PromptType
    brand: str
    win_rate: float
    share_of_voice: float  # complementary to DWR: win_rate + 0.5 * (alternatives / total)
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


class GroundingSource(BaseModel):
    """A web source cited by Gemini grounding (one per grounding_chunk)."""

    id: str | None = None  # DB row id, set after insert
    response_id: str = ""  # FK → gemini_responses.id, assigned by the caller
    web_title: str
    domain: str  # parsed from web.title (uri is an opaque redirect token); "" when unparseable
    chunk_index: int = 0  # position in grounding_chunks (linking aid, not a column)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class GroundingSupport(BaseModel):
    """A response-text segment backed by grounding (one per grounding_support)."""

    id: str | None = None  # DB row id, set after insert
    response_id: str = ""  # FK → gemini_responses.id, assigned by the caller
    source_id: str | None = None  # FK → grounding_sources.id, linked at save time
    source_chunk_index: int | None = None  # first cited chunk (linking aid, not a column)
    segment_start: int
    segment_end: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SourceImpactRow(BaseModel):
    """Derived-on-read impact of a cited domain over the focus brand's DWR."""

    domain: str
    citations: int  # number of source rows citing this domain
    direct_wins: int  # responses citing the domain where the focus brand was a Direct Winner
    impact_ratio: float  # direct_wins / citations
