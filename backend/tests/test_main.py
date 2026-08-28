"""Integration tests for the /api/evaluate pipeline (mocked DB + Gemini).

run_evaluation schedules a background job; the real evaluation lifecycle runs in
_ execute_evaluation. External systems (Supabase + Gemini) are mocked while the
wiring logic under test — focus-brand consistency over per-type DWR and its
persistence — runs for real.
"""

import asyncio
import statistics
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from aeo_engine.main import _execute_evaluation, _sample_and_store_prompt, app
from aeo_engine.models import (
    Classification,
    ClassificationResult,
    Competitor,
    GeminiResponse,
    MetricSummary,
    PromptRecord,
    PromptType,
)

client = TestClient(app)

FOCUS_BRAND = "Linear"
PER_TYPE_RATES = [0.5, 0.75, 1.0, 0.25, 0.6]

# Google Search grounding shape as persisted by gemini.py (model_dump json).
GROUNDING = {
    "grounding_chunks": [
        {"web": {"title": "Linear Review 2025 | linear.app", "uri": "https://r.redirect/1"}},
        {"web": {"title": "Compare tools on g2.com", "uri": "https://r.redirect/2"}},
    ],
    "grounding_supports": [
        {"segment": {"start_index": 0, "end_index": 52}, "grounding_chunk_indices": [0]},
        {"segment": {"start_index": 60, "end_index": 120}, "grounding_chunk_indices": [1]},
    ],
    "web_search_queries": [],
}


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
        _metric(pt, FOCUS_BRAND, rate) for pt, rate in zip(types, PER_TYPE_RATES, strict=True)
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
        assert {"consistency": pytest.approx(expected)} in [args[1] for args in update_args]

        # The completion update still happens and carries status.
        assert any(args[1].get("status") == "completed" for args in update_args)


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
        mock_metrics.return_value = [_metric(PromptType.DIRECT, FOCUS_BRAND, 0.6)]

        await _execute_evaluation(
            evaluation_id="eval-1",
            corpus=_corpus()[:1],
            all_brands=[FOCUS_BRAND],
            n=2,
        )

        for call in mock_update.call_args_list:
            assert "consistency" not in call.args[1]


def test_resolve_competitors_404_when_empty_result() -> None:
    """Mirror resolve_category: an empty competitor list is a 404 with a detail
    message, never a silent 200 + empty list."""
    with patch(
        "aeo_engine.main.resolve_brand_competitors",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = []
        res = client.get(
            "/api/resolve-competitors",
            params={"brand": "Linear", "category": "project management"},
        )
    assert res.status_code == 404
    assert res.json()["detail"] == "Could not resolve competitors for 'Linear'"


def test_resolve_competitors_200_with_competitors() -> None:
    """A non-empty result still returns 200 with the parsed competitors."""
    with patch(
        "aeo_engine.main.resolve_brand_competitors",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = [Competitor(name="Jira", reason="a PM rival")]
        res = client.get(
            "/api/resolve-competitors",
            params={"brand": "Linear", "category": "project management"},
        )
    assert res.status_code == 200
    assert res.json()["competitors"] == [{"name": "Jira", "reason": "a PM rival"}]


def test_resolve_competitors_400_on_empty_brand() -> None:
    """An empty brand stays a 400 (mirrors resolve_category)."""
    res = client.get(
        "/api/resolve-competitors",
        params={"brand": "", "category": "project management"},
    )
    assert res.status_code == 400


def test_resolve_competitors_400_on_empty_category() -> None:
    """An empty category stays a 400 (mirrors resolve_category)."""
    res = client.get(
        "/api/resolve-competitors",
        params={"brand": "Linear", "category": ""},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_sample_and_store_persists_grounding_sources() -> None:
    """Responses with grounding metadata have their sources + supports
    extracted and persisted once, keyed by the response id. Responses without
    grounding are skipped entirely."""
    grounded = GeminiResponse(
        id="resp-1",
        evaluation_id="eval-1",
        prompt_id="direct-01",
        run_index=1,
        model_id="gemini-3.6-flash",
        raw_text="Linear is the best project management tool for teams.",
        grounding_metadata=GROUNDING,
    )
    plain = GeminiResponse(
        id="resp-2",
        evaluation_id="eval-1",
        prompt_id="direct-01",
        run_index=2,
        model_id="gemini-3.6-flash",
        raw_text="Jira is the best project management tool for teams.",
        grounding_metadata=None,
    )
    with (
        patch("aeo_engine.main.save_responses"),
        patch("aeo_engine.main.save_grounding_sources") as mock_grounding,
        patch("aeo_engine.main.run_parallel_sampling", new_callable=AsyncMock) as mock_sampling,
        patch("aeo_engine.main.classify_all_brands") as mock_classify,
    ):
        mock_sampling.return_value = [grounded, plain]
        mock_classify.return_value = []

        await _sample_and_store_prompt(
            prompt=PromptRecord(
                id="direct-01",
                prompt_type=PromptType.DIRECT,
                text="What is the best project management tool?",
            ),
            evaluation_id="eval-1",
            all_brands=[FOCUS_BRAND, "Jira"],
            n=2,
            semaphore=asyncio.Semaphore(1),
        )

        # Only the grounded response is persisted — exactly once.
        assert mock_grounding.call_count == 1
        response_id, sources, supports = mock_grounding.call_args.args
        assert response_id == "resp-1"
        assert [s.domain for s in sources] == ["linear.app", "g2.com"]
        assert [s.chunk_index for s in sources] == [0, 1]
        assert all(s.response_id == "resp-1" for s in sources)
        assert [(sp.segment_start, sp.segment_end, sp.source_chunk_index) for sp in supports] == [
            (0, 52, 0),
            (60, 120, 1),
        ]
        assert all(sp.response_id == "resp-1" for sp in supports)


def test_get_evaluation_detail_includes_source_impact() -> None:
    """The detail endpoint ranks cited domains by DWR co-occurrence for the
    focus brand — scoping to the focus brand only, degrading to [] without
    grounding data."""
    source_rows = [
        {
            "id": "s1",
            "response_id": "r1",
            "web_title": "Linear Review | linear.app",
            "domain": "linear.app",
        },
        {"id": "s2", "response_id": "r1", "web_title": "Compare on g2.com", "domain": "g2.com"},
        {
            "id": "s3",
            "response_id": "r2",
            "web_title": "Another linear.app page",
            "domain": "linear.app",
        },
    ]
    classification_rows = [
        {
            "response_id": "r1",
            "brand": FOCUS_BRAND,
            "classification": "direct_winner",
            "first_mention_position": None,
            "mention_count": 1,
            "confidence_score": 0.9,
        },
        {
            "response_id": "r2",
            "brand": FOCUS_BRAND,
            "classification": "alternative_mention",
            "first_mention_position": None,
            "mention_count": 1,
            "confidence_score": 0.8,
        },
        # Competitor classification must NOT leak into the focus brand's impact.
        {
            "response_id": "r2",
            "brand": "Jira",
            "classification": "direct_winner",
            "first_mention_position": None,
            "mention_count": 1,
            "confidence_score": 0.8,
        },
    ]
    with (
        patch(
            "aeo_engine.main.get_evaluation",
            return_value={"id": "eval-1", "brand": FOCUS_BRAND},
        ),
        patch("aeo_engine.main.get_responses", return_value=[]),
        patch("aeo_engine.main.get_classifications", return_value=classification_rows),
        patch("aeo_engine.main.get_metrics", return_value=[]),
        patch("aeo_engine.main.get_grounding_sources_for_evaluation", return_value=source_rows),
    ):
        res = client.get("/api/evaluations/eval-1")

    assert res.status_code == 200
    payload = res.json()
    # linear.app: 2 citations, r1 is a focus-brand direct winner, r2 is not → 1 win.
    # g2.com: 1 citation, r1 direct winner → 1 win.
    assert payload["source_impact"] == [
        {"domain": "linear.app", "citations": 2, "direct_wins": 1, "impact_ratio": 0.5},
        {"domain": "g2.com", "citations": 1, "direct_wins": 1, "impact_ratio": 1.0},
    ]


def test_get_evaluation_detail_source_impact_degrades_without_grounding() -> None:
    """No grounding sources → source_impact is an empty list, never a crash."""
    with (
        patch(
            "aeo_engine.main.get_evaluation",
            return_value={"id": "eval-1", "brand": FOCUS_BRAND},
        ),
        patch("aeo_engine.main.get_responses", return_value=[]),
        patch("aeo_engine.main.get_classifications", return_value=[]),
        patch("aeo_engine.main.get_metrics", return_value=[]),
        patch("aeo_engine.main.get_grounding_sources_for_evaluation", return_value=[]),
    ):
        res = client.get("/api/evaluations/eval-1")

    assert res.status_code == 200
    assert res.json()["source_impact"] == []
