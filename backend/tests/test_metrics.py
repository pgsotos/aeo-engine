"""Tests for metrics computation (pure functions)."""

import statistics

import pytest

from aeo_engine.metrics import (
    compute_consistency,
    compute_metrics,
    compute_share_of_voice,
    wilson_score_interval,
)
from aeo_engine.models import Classification, ClassificationResult, PromptType


def test_wilson_score_perfect_score() -> None:
    """All wins → CI should be tight around 1.0."""
    lower, upper = wilson_score_interval(8, 8)
    assert upper == 1.0
    assert lower > 0.5  # should be high


def test_wilson_score_zero_wins() -> None:
    """No wins → CI should be tight around 0.0."""
    lower, upper = wilson_score_interval(0, 8)
    assert lower == 0.0
    assert upper < 0.5  # should be low


def test_wilson_score_half() -> None:
    """50% wins → CI should straddle 0.5."""
    lower, upper = wilson_score_interval(4, 8)
    assert lower < 0.5 < upper


def test_wilson_score_empty() -> None:
    """No trials → return full range."""
    lower, upper = wilson_score_interval(0, 0)
    assert lower == 0.0
    assert upper == 1.0


def test_compute_metrics_basic() -> None:
    """Compute metrics from a list of classifications."""
    classifications = [
        ClassificationResult(
            response_id="r1",
            brand="Linear",
            classification=Classification.DIRECT_WINNER,
            mention_count=3,
            confidence_score=0.9,
        ),
        ClassificationResult(
            response_id="r2",
            brand="Linear",
            classification=Classification.ALTERNATIVE_MENTION,
            mention_count=1,
            confidence_score=0.7,
        ),
        ClassificationResult(
            response_id="r3",
            brand="Linear",
            classification=Classification.OMITTED,
            mention_count=0,
            confidence_score=1.0,
        ),
    ]
    metric = compute_metrics(classifications, PromptType.DIRECT, "eval-1", "Linear")
    assert metric.total_runs == 3
    assert metric.direct_wins == 1
    assert metric.alternative_mentions == 1
    assert metric.omitted == 1
    assert 0.0 <= metric.win_rate <= 1.0
    assert metric.ci_lower <= metric.win_rate <= metric.ci_upper


# ── Share of Voice ──────────────────────────────────────────────────────────


def test_share_of_voice_no_alternatives() -> None:
    """No alternative mentions → SoV equals the win rate."""
    assert compute_share_of_voice(0.5, 0, 8) == pytest.approx(0.5)


def test_share_of_voice_all_alternatives() -> None:
    """Every run is an alternative mention → SoV is half the win-rate weight."""
    assert compute_share_of_voice(0.0, 8, 8) == pytest.approx(0.5)


def test_share_of_voice_formula() -> None:
    """SoV = win_rate + 0.5 * (alternatives / total)."""
    assert compute_share_of_voice(0.4, 3, 8) == pytest.approx(0.4 + 0.5 * (3 / 8))


def test_share_of_voice_clamped_at_one() -> None:
    """Perfect win rate plus alternatives must not push SoV above 1.0."""
    assert compute_share_of_voice(1.0, 4, 8) == pytest.approx(1.0)


def test_share_of_voice_zero_runs() -> None:
    """No runs → SoV is 0.0 (no division by zero)."""
    assert compute_share_of_voice(0.0, 0, 0) == pytest.approx(0.0)


def test_compute_metrics_populates_share_of_voice() -> None:
    """compute_metrics wires SoV from direct wins and alternative mentions."""
    classifications = [
        ClassificationResult(
            response_id="r1",
            brand="Linear",
            classification=Classification.DIRECT_WINNER,
        ),
        ClassificationResult(
            response_id="r2",
            brand="Linear",
            classification=Classification.ALTERNATIVE_MENTION,
        ),
        ClassificationResult(
            response_id="r3",
            brand="Linear",
            classification=Classification.OMITTED,
        ),
    ]
    metric = compute_metrics(classifications, PromptType.DIRECT, "eval-1", "Linear")
    # 1/3 win rate + 0.5 * (1/3 alternatives) = 1/2
    assert metric.share_of_voice == pytest.approx(0.5)
    assert 0.0 <= metric.share_of_voice <= 1.0


# ── Consistency Score ────────────────────────────────────────────────────────


def test_compute_consistency_zero_variance() -> None:
    """All per-type DWR identical → perfect consistency (1.0)."""
    assert compute_consistency([0.8, 0.8, 0.8, 0.8, 0.8]) == pytest.approx(1.0)


def test_compute_consistency_varied_rates() -> None:
    """Consistency = 1 - population stddev of per-type DWR."""
    rates = [0.5, 0.75, 1.0, 0.25, 0.6]
    assert compute_consistency(rates) == pytest.approx(1 - statistics.pstdev(rates))


def test_compute_consistency_empty_returns_none() -> None:
    """No per-type rates → not computable, None (never raises)."""
    assert compute_consistency([]) is None


def test_compute_consistency_single_type_returns_none() -> None:
    """One per-type rate → not computable, None."""
    assert compute_consistency([0.6]) is None
