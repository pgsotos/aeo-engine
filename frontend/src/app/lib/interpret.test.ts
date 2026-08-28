import { describe, expect, it } from "vitest";

import type { DashboardData, MetricSummary, PromptType } from "../types";
import { interpretEvaluation } from "./interpret";

/** Build a minimal dashboard from per-brand, per-type win rates. */
function dashboardFor(
  brand: string,
  byBrand: Record<string, Partial<Record<PromptType, number>>>,
): DashboardData {
  const metrics: MetricSummary[] = [];
  for (const [b, types] of Object.entries(byBrand)) {
    for (const [pt, winRate] of Object.entries(types) as [PromptType, number][]) {
      metrics.push({
        evaluation_id: "e1",
        prompt_type: pt,
        brand: b,
        win_rate: winRate,
        share_of_voice: null,
        ci_lower: winRate - 0.05,
        ci_upper: winRate + 0.05,
        total_runs: 8,
        direct_wins: Math.round(winRate * 8),
        alternative_mentions: 0,
        omitted: 0,
      });
    }
  }
  return {
    evaluation: {
      id: "e1",
      brand,
      category: "project management",
      sampling_n: 8,
      status: "completed",
      consistency: 0.9,
      created_at: "2026-01-01T00:00:00Z",
      completed_at: "2026-01-01T01:00:00Z",
    },
    metrics,
    responses: [],
    classifications: [],
  };
}

describe("interpretEvaluation", () => {
  it("classifies a brand that clears 60% everywhere as strong", () => {
    const i = interpretEvaluation(
      dashboardFor("Linear", {
        Linear: {
          direct: 0.9,
          comparative: 0.8,
          use_case: 0.85,
          feature: 0.75,
          negative: 0.7,
        },
      }),
    );

    expect(i.verdictTone).toBe("strong");
    expect(i.focusWinRate).toBeCloseTo(0.8, 5);
    expect(i.strengths).toHaveLength(5);
    expect(i.weaknesses).toHaveLength(0);
    expect(i.incomplete).toBe(false);
  });

  it("orders strengths strongest-first and weaknesses weakest-first", () => {
    const i = interpretEvaluation(
      dashboardFor("BrandX", {
        BrandX: {
          direct: 0.9,
          comparative: 0.35,
          use_case: 0.65,
          feature: 0.2,
          negative: 0.3,
        },
      }),
    );

    expect(i.strengths.map((s) => s.type)).toEqual(["direct", "use_case"]);
    expect(i.weaknesses.map((w) => w.type)).toEqual(["feature", "negative", "comparative"]);
  });

  it("flags incomplete when not all five prompt types are scored", () => {
    const i = interpretEvaluation(
      dashboardFor("Linear", { Linear: { direct: 0.9 } }),
    );
    expect(i.incomplete).toBe(true);
  });

  it("reports competitors whose aggregate win rate beats the focus brand", () => {
    const i = interpretEvaluation(
      dashboardFor("BrandA", {
        BrandA: { direct: 0.6, comparative: 0.6, use_case: 0.6, feature: 0.6, negative: 0.6 },
        BrandB: { direct: 0.9, comparative: 0.9, use_case: 0.9, feature: 0.9, negative: 0.9 },
        BrandC: { direct: 0.2, comparative: 0.2, use_case: 0.2, feature: 0.2, negative: 0.2 },
      }),
    );

    expect(i.competitorsAhead).toHaveLength(1);
    expect(i.competitorsAhead[0].brand).toBe("BrandB");
    expect(i.competitorsAhead[0].delta).toBe(30);
  });

  it("marks a sub-40% brand as weak", () => {
    const i = interpretEvaluation(
      dashboardFor("BrandZ", {
        BrandZ: {
          direct: 0.2,
          comparative: 0.2,
          use_case: 0.2,
          feature: 0.2,
          negative: 0.2,
        },
      }),
    );
    expect(i.verdictTone).toBe("weak");
  });

  it("returns empty insight lists when the focus brand has no metrics", () => {
    const i = interpretEvaluation(
      dashboardFor("Ghost", { Other: { direct: 0.9 } }),
    );
    expect(i.verdictTone).toBe("weak");
    expect(i.strengths).toHaveLength(0);
    expect(i.weaknesses).toHaveLength(0);
  });
});
