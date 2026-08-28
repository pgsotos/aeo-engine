import type { DashboardData, MetricSummary, PromptType } from "../types";
import { PROMPT_TYPES } from "../constants";

/**
 * Deterministic interpretation layer for the evaluation detail view.
 *
 * Turns the raw metrics every number on the dashboard is derived from into a
 * plain-language verdict a non-technical stakeholder can read in seconds. This
 * is presentation logic only — it never recomputes the underlying metric, it
 * only aggregates and labels what the backend already produced.
 *
 * These thresholds mirror the Heatmap colouring so the prose always agrees
 * with the visuals: >= 60% is strong, < 40% is weak, in between contested.
 */

export const STRONG_THRESHOLD = 0.6;
export const WEAK_THRESHOLD = 0.4;

export type VerdictTone = "strong" | "contested" | "weak";

export interface TypeInsight {
  type: PromptType;
  winRate: number;
}

export interface CompetitorInsight {
  brand: string;
  winRate: number;
  /** Positive when the competitor beats the focus brand. */
  delta: number;
}

export interface EvaluationInterpretation {
  /** Aggregate win rate across the focus brand's prompt types. */
  focusWinRate: number;
  /** Aggregate Wilson CI for the focus brand. */
  ciLower: number;
  ciUpper: number;
  verdictTone: VerdictTone;
  /**
   * Prompt types where the focus brand clears the strong threshold.
   * Ordered strongest first.
   */
  strengths: TypeInsight[];
  /**
   * Prompt types where the focus brand falls below the weak threshold.
   * Ordered weakest first.
   */
  weaknesses: TypeInsight[];
  /**
   * Competitors whose aggregate win rate beats the focus brand's, delta in
   * points (0..100 scale). Ordered most ahead first.
   */
  competitorsAhead: CompetitorInsight[];
  /** True when not all five prompt types have a metric for the focus brand. */
  incomplete: boolean;
}

/** Average of the focus brand's win rates across the prompt types it scored. */
function aggregateWinRate(metrics: MetricSummary[], brand: string): number {
  const focus = metrics.filter((m) => m.brand === brand);
  if (focus.length === 0) return 0;
  const sum = focus.reduce((acc, m) => acc + m.win_rate, 0);
  return sum / focus.length;
}

/** Average of the focus brand's CI bounds across scored prompt types. */
function aggregateCi(metrics: MetricSummary[], brand: string): { lower: number; upper: number } {
  const focus = metrics.filter((m) => m.brand === brand);
  if (focus.length === 0) return { lower: 0, upper: 0 };
  const lower = focus.reduce((acc, m) => acc + m.ci_lower, 0) / focus.length;
  const upper = focus.reduce((acc, m) => acc + m.ci_upper, 0) / focus.length;
  return { lower, upper };
}

function toneFor(winRate: number): VerdictTone {
  if (winRate >= STRONG_THRESHOLD) return "strong";
  if (winRate < WEAK_THRESHOLD) return "weak";
  return "contested";
}

export function interpretEvaluation(
  dashboard: DashboardData,
): EvaluationInterpretation {
  const brand = dashboard.evaluation.brand;
  const metrics = dashboard.metrics;

  const focusTypes = metrics
    .filter((m) => m.brand === brand)
    .map((m) => ({ type: m.prompt_type, winRate: m.win_rate }));

  const strengths = focusTypes
    .filter((t) => t.winRate >= STRONG_THRESHOLD)
    .sort((a, b) => b.winRate - a.winRate);
  const weaknesses = focusTypes
    .filter((t) => t.winRate < WEAK_THRESHOLD)
    .sort((a, b) => a.winRate - b.winRate);

  const focusWinRate = aggregateWinRate(metrics, brand);
  const { lower, upper } = aggregateCi(metrics, brand);

  // Aggregate per-competitor win rates too, so we compare like with like.
  const brands = Array.from(new Set(metrics.map((m) => m.brand)));
  const competitorsAhead = brands
    .filter((b) => b !== brand)
    .map((b) => ({ brand: b, winRate: aggregateWinRate(metrics, b) }))
    .filter((c) => c.winRate > focusWinRate)
    .map((c) => ({
      ...c,
      delta: Math.round((c.winRate - focusWinRate) * 100),
    }))
    .sort((a, b) => b.delta - a.delta);

  const completedTypes = new Set(focusTypes.map((t) => t.type));
  const incomplete = PROMPT_TYPES.some((t) => !completedTypes.has(t));

  return {
    focusWinRate,
    ciLower: lower,
    ciUpper: upper,
    verdictTone: toneFor(focusWinRate),
    strengths,
    weaknesses,
    competitorsAhead,
    incomplete,
  };
}
