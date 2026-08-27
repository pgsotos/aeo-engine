"""Metrics computation: Win Rate with confidence intervals.

Uses the Wilson score interval for binomial proportions, which is
appropriate for small sample sizes and doesn't require normal approximation.
"""

from __future__ import annotations

import math

from aeo_engine.models import (
    Classification,
    ClassificationResult,
    MetricSummary,
    PromptType,
)


def wilson_score_interval(
    successes: int, trials: int, z: float = 1.96
) -> tuple[float, float]:
    """Compute the Wilson score confidence interval for a binomial proportion.

    Args:
        successes: Number of successful outcomes (direct wins)
        trials: Total number of trials
        z: Z-score for desired confidence level (1.96 = 95%)

    Returns:
        (lower_bound, upper_bound) of the confidence interval
    """
    if trials == 0:
        return (0.0, 1.0)

    p_hat = successes / trials
    denominator = 1 + z**2 / trials
    centre = p_hat + z**2 / (2 * trials)
    spread = z * math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * trials)) / trials)

    lower = max(0.0, (centre - spread) / denominator)
    upper = min(1.0, (centre + spread) / denominator)

    return (round(lower, 4), round(upper, 4))


def compute_share_of_voice(win_rate: float, alternatives: int, total: int) -> float:
    """Compute Share of Voice: DWR plus half the alternative-mention share.

    Complementary to Direct Answer Win Rate — it rewards presence in answers
    even when the brand is not the direct recommendation. Clamped to [0, 1];
    returns 0.0 when there are no runs to avoid division by zero.
    """
    if total <= 0:
        return 0.0
    raw = win_rate + 0.5 * (alternatives / total)
    return min(1.0, max(0.0, raw))


def compute_metrics(
    classifications: list[ClassificationResult],
    prompt_type: PromptType,
    evaluation_id: str,
    brand: str,
) -> MetricSummary:
    """Compute Win Rate and confidence interval for a set of classifications.

    Pure function: same inputs → same output.
    """
    total = len(classifications)
    direct_wins = sum(
        1 for c in classifications if c.classification == Classification.DIRECT_WINNER
    )
    alternatives = sum(
        1
        for c in classifications
        if c.classification == Classification.ALTERNATIVE_MENTION
    )
    omitted = sum(
        1 for c in classifications if c.classification == Classification.OMITTED
    )

    win_rate = direct_wins / total if total > 0 else 0.0
    ci_lower, ci_upper = wilson_score_interval(direct_wins, total)
    share_of_voice = compute_share_of_voice(win_rate, alternatives, total)

    return MetricSummary(
        evaluation_id=evaluation_id,
        prompt_type=prompt_type,
        brand=brand,
        win_rate=round(win_rate, 4),
        share_of_voice=round(share_of_voice, 4),
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        total_runs=total,
        direct_wins=direct_wins,
        alternative_mentions=alternatives,
        omitted=omitted,
    )


def compute_all_metrics(
    all_classifications: list[ClassificationResult],
    prompt_type_map: dict[str, PromptType],
    evaluation_id: str,
    brands: list[str],
) -> list[MetricSummary]:
    """Compute metrics for every brand × prompt_type combination.

    Args:
        all_classifications: All classification results for the evaluation
        prompt_type_map: mapping from prompt_id → PromptType
        evaluation_id: the evaluation these belong to
        brands: list of brands to compute metrics for
    """
    metrics: list[MetricSummary] = []

    for brand in brands:
        brand_classifications = [c for c in all_classifications if c.brand == brand]

        # Group by prompt type using the response_id → prompt mapping
        # We need to know which prompt_type each classification came from
        # This is handled by the caller grouping before passing here

        # For now, compute overall metrics
        overall = compute_metrics(
            brand_classifications, PromptType.DIRECT, evaluation_id, brand
        )
        metrics.append(overall)

    return metrics


def compute_per_type_metrics(
    classifications_by_type: dict[PromptType, list[ClassificationResult]],
    evaluation_id: str,
    brands: list[str],
) -> list[MetricSummary]:
    """Compute metrics broken down by prompt type.

    This is the multi-dimension analysis core.
    """
    metrics: list[MetricSummary] = []

    for prompt_type, type_classifications in classifications_by_type.items():
        for brand in brands:
            brand_in_type = [c for c in type_classifications if c.brand == brand]
            metric = compute_metrics(brand_in_type, prompt_type, evaluation_id, brand)
            metrics.append(metric)

    return metrics
