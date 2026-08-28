"""Integration tests for the /api/evaluate pipeline (mocked DB + Gemini).

run_evaluation schedules a background job; the real evaluation lifecycle runs in
_ execute_evaluation. External systems (Supabase + Gemini) are mocked while the
wiring logic under test — focus-brand consistency over per-type DWR and its
persistence — runs for real.
"""

import statistics
from unittest.mock import AsyncMock, patch

import pytest

from aeo_engine.main import _execute_evaluation
from aeo_engine.models import (
    Classification,
    ClassificationResult,
    MetricSummary,
    PromptRecord,
    PromptType,
)

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
        for pt, rate in zip(types, PER_TYPE_RATES, strict=True)
    ]
    # Competitor must NOT leak into the focus brand's consistency window.
    metrics.append(_metric(PromptType.DIRECT, "Jira", 0.99))
    return metrics


def _corpus() -> list[PromptRecord]:
    """One prompt per type so the focus brand has five per-type DWR rates."""
    return [
        PromptRecord(
            id=f"prompt-{i}",
            prompt_type=pt,
            text=f"compare {FOCUS_BRAND} vs Jira #{i}",
        )
        for i, pt in enumerate(
            [
                PromptType.DIRECT,
                PromptType.COMPARATIVE,
                PromptType.USE_CASE,
                PromptType.FEATURE,
                PromptType.NEGATIVE,
            ]
        )
    ]


@pytest.mark.asyncio
async def test_execute_evaluation_persists_consistency_for_focus_brand() -> None:
    """After save_metrics, consistency (1 - pstdev over the focus brand's
    per-type DWR) is persisted on the evaluation, and the competitor's metric
    does not leak into the consistency window."""
    with (
        patch("aeo_engine.main.save_classifications"),
        patch("aeo_engine.main.save_metrics"),
        patch("aeo_engine.main.update_evaluation") as mock_update,
        patch(
            "aeo_engine.main._sample_and_store_prompt",
            new_callable=AsyncMock,
        ) as mock_sample,
        patch("aeo_engine.main.compute_per_type_metrics") as mock_metrics,
    ):
        mock_sample.return_value = [
            ClassificationResult(
                response_id="r0",
                brand=FOCUS_BRAND,
                classification=Classification.DIRECT_WINNER,
            )
        ]  # a non-empty classification set so the job advances past the empty check
        mock_metrics.return_value = _linear_metrics()

        await _execute_evaluation(
            evaluation_id="eval-1",
            corpus=_corpus(),
            all_brands=[FOCUS_BRAND, "Jira"],
            n=2,
        )

        expected = 1 - statistics.pstdev(PER_TYPE_RATES)
        update_args = [call.args for call in mock_update.call_args_list]
        assert {
            "consistency": pytest.approx(expected)
        } in [args[1] for args in update_args]

        # The completion update still happens and carries status.
        assert any(
            args[1].get("status") == "completed"
            for args in update_args
        )


@pytest.mark.asyncio
async def test_execute_evaluation_skips_consistency_when_single_type() -> None:
    """Fewer than two per-type DWR rates → consistency is not computable and
    no consistency update is issued."""
    with (
        patch("aeo_engine.main.save_classifications"),
        patch("aeo_engine.main.save_metrics"),
        patch("aeo_engine.main.update_evaluation") as mock_update,
        patch(
            "aeo_engine.main._sample_and_store_prompt",
            new_callable=AsyncMock,
        ) as mock_sample,
        patch("aeo_engine.main.compute_per_type_metrics") as mock_metrics,
    ):
        mock_sample.return_value = []
        mock_metrics.return_value = [
            _metric(PromptType.DIRECT, FOCUS_BRAND, 0.6)
        ]

        await _execute_evaluation(
            evaluation_id="eval-1",
            corpus=_corpus()[:1],
            all_brands=[FOCUS_BRAND],
            n=2,
        )

        for call in mock_update.call_args_list:
            assert "consistency" not in call.args[1]
