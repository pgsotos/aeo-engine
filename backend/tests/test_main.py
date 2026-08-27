"""Integration tests for the /api/evaluate pipeline (mocked DB + Gemini).

run_evaluation has a real dependency boundary (Supabase + Gemini), so the
external systems are mocked while the wiring logic under test — per-brand
filtering, real compute_consistency, and persistence — runs for real.
"""

import statistics
from unittest.mock import AsyncMock, patch

import pytest

from aeo_engine.main import EvaluateRequest, run_evaluation
from aeo_engine.models import MetricSummary, PromptType

FOCUS_BRAND = "Linear"
PER_TYPE_RATES = [0.5, 0.75, 1.0, 0.25, 0.6]


def _metric(prompt_type: PromptType, brand: str, win_rate: float) -> MetricSummary:
    """Build a single MetricSummary row on the metrics table's grain."""
    return MetricSummary(
        evaluation_id="eval-1",
        prompt_type=prompt_type,
        brand=brand,
        win_rate=win_rate,
        share_of_voice=win_rate,
        ci_lower=0.0,
        ci_upper=1.0,
        total_runs=8,
        direct_wins=round(win_rate * 8),
        alternative_mentions=0,
        omitted=0,
    )


def _linear_metrics() -> list[MetricSummary]:
    """Five per-type metrics for the focus brand plus one competitor metric."""
    types = [
        PromptType.DIRECT,
        PromptType.COMPARATIVE,
        PromptType.USE_CASE,
        PromptType.FEATURE,
        PromptType.NEGATIVE,
    ]
    metrics = [
        _metric(pt, FOCUS_BRAND, rate)
        for pt, rate in zip(types, PER_TYPE_RATES)
    ]
    # Competitor must NOT leak into the focus brand's consistency window.
    metrics.append(_metric(PromptType.DIRECT, "Jira", 0.99))
    return metrics


@pytest.mark.asyncio
async def test_run_evaluation_persists_consistency_for_focus_brand() -> None:
    """After save_metrics, consistency (1 - pstdev over the brand's per-type
    DWR) is persisted on the evaluation."""
    with (
        patch("aeo_engine.main.create_evaluation"),
        patch("aeo_engine.main.save_metrics"),
        patch("aeo_engine.main.update_evaluation") as mock_update,
        patch(
            "aeo_engine.main.run_parallel_sampling", new_callable=AsyncMock
        ) as mock_sampling,
        patch("aeo_engine.main.classify_all_brands") as mock_classify,
        patch("aeo_engine.main.compute_per_type_metrics") as mock_metrics,
        patch("aeo_engine.main.generate_corpus") as mock_corpus,
    ):
        mock_sampling.return_value = []
        mock_classify.return_value = []
        mock_metrics.return_value = _linear_metrics()
        mock_corpus.return_value = []

        result = await run_evaluation(
            EvaluateRequest(
                brand=FOCUS_BRAND,
                category="project management",
                competitors=["Jira"],
                sampling_n=2,
            )
        )

        assert result["status"] == "completed"

        expected = 1 - statistics.pstdev(PER_TYPE_RATES)
        update_args = [call.args for call in mock_update.call_args_list]
        assert {"consistency": pytest.approx(expected)} in [args[1] for args in update_args]

        # The completion update still happens and carries status.
        assert any(
            args[1].get("status") == "completed" for args in update_args
        )


@pytest.mark.asyncio
async def test_run_evaluation_skips_consistency_when_single_type() -> None:
    """Fewer than two per-type DWR rates → consistency is not computable and
    no consistency update is issued."""
    with (
        patch("aeo_engine.main.create_evaluation"),
        patch("aeo_engine.main.save_metrics"),
        patch("aeo_engine.main.update_evaluation") as mock_update,
        patch(
            "aeo_engine.main.run_parallel_sampling", new_callable=AsyncMock
        ) as mock_sampling,
        patch("aeo_engine.main.classify_all_brands") as mock_classify,
        patch("aeo_engine.main.compute_per_type_metrics") as mock_metrics,
        patch("aeo_engine.main.generate_corpus") as mock_corpus,
    ):
        mock_sampling.return_value = []
        mock_classify.return_value = []
        mock_metrics.return_value = [
            _metric(PromptType.DIRECT, FOCUS_BRAND, 0.6)
        ]
        mock_corpus.return_value = []

        result = await run_evaluation(
            EvaluateRequest(
                brand=FOCUS_BRAND,
                category="project management",
                competitors=["Jira"],
                sampling_n=2,
            )
        )

        assert result["status"] == "completed"
        for call in mock_update.call_args_list:
            assert "consistency" not in call.args[1]
