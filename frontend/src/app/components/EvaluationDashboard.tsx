"use client";

import { useMemo } from "react";
import { PROMPT_TYPES } from "../constants";
import type {
  ClassificationResult,
  DashboardData,
  MetricSummary,
  PromptType,
} from "../types";
import { interpretEvaluation } from "../lib/interpret";
import ConfidenceBar from "./ConfidenceBar";
import DashboardHeader from "./DashboardHeader";
import DashboardLegend from "./DashboardLegend";
import ExecutiveSummary from "./ExecutiveSummary";
import Heatmap from "./Heatmap";
import ResponseCard from "./ResponseCard";
import SourceAuditor from "./SourceAuditor";

interface EvaluationDashboardProps {
  dashboard: DashboardData;
  loading: boolean;
  onBack: () => void;
}

/**
 * The results view for one evaluation.
 *
 * Reads top-down at decreasing altitude: the heatmap compares every brand
 * across every prompt type, the confidence bars narrow to the focus brand,
 * and the response cards expose the raw text each number was derived from —
 * so any figure on the page can be traced back to the answer that produced it.
 */
export default function EvaluationDashboard({
  dashboard,
  loading,
  onBack,
}: EvaluationDashboardProps) {
  const { evaluation, metrics, responses, classifications } = dashboard;

  /** Metrics for the focus brand, indexed by prompt type. */
  const focusByType = useMemo(() => {
    const map = new Map<PromptType, MetricSummary>();
    for (const m of metrics) {
      if (m.brand === evaluation.brand) map.set(m.prompt_type, m);
    }
    return map;
  }, [metrics, evaluation.brand]);

  /** Classifications grouped by the response they belong to. */
  const classificationsByResponse = useMemo(() => {
    const map = new Map<string, ClassificationResult[]>();
    for (const cls of classifications) {
      const arr = map.get(cls.response_id) ?? [];
      arr.push(cls);
      map.set(cls.response_id, arr);
    }
    return map;
  }, [classifications]);

  /** Deterministic plain-language reading of the metrics. */
  const interpretation = useMemo(() => interpretEvaluation(dashboard), [dashboard]);

  return (
    <div className="space-y-8">
      <DashboardHeader evaluation={evaluation} onBack={onBack} />
      <DashboardLegend samplingN={evaluation.sampling_n} />

      {loading ? (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 py-12 text-center text-zinc-500">
          Loading dashboard…
        </div>
      ) : (
        <>
          <ExecutiveSummary
            interpretation={interpretation}
            evaluation={evaluation}
          />

          <section>
            <h2 className="mb-4 text-lg font-semibold text-zinc-200">
              Multi-Dimension Heatmap
            </h2>
            <Heatmap metrics={metrics} />
          </section>

          {focusByType.size > 0 && (
            <section>
              <h2 className="mb-4 text-lg font-semibold text-zinc-200">
                {evaluation.brand} Win Rate by Prompt Type
              </h2>
              <div className="space-y-4 rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
                {PROMPT_TYPES.map((type) => {
                  const metric = focusByType.get(type);
                  return metric ? (
                    <ConfidenceBar key={type} metric={metric} />
                  ) : null;
                })}
              </div>
            </section>
          )}

          <section>
            <h2 className="mb-4 text-lg font-semibold text-zinc-200">
              Source Auditor
            </h2>
            <SourceAuditor rows={dashboard.source_impact ?? []} />
          </section>

          {responses.length > 0 && (
            <section>
              <details className="group rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
                <summary className="flex list-none cursor-pointer items-center justify-between text-lg font-semibold text-zinc-200">
                  <span>
                    Individual Responses ({responses.length})
                  </span>
                  <span className="text-sm font-normal text-zinc-500 group-open:hidden">
                    Expand to trace each answer
                  </span>
                  <span className="text-sm font-normal text-zinc-500 hidden group-open:inline">
                    Collapse
                  </span>
                </summary>
                <div className="mt-4 space-y-3">
                  {responses.map((resp) => (
                    <ResponseCard
                      key={resp.id}
                      response={resp}
                      classifications={classificationsByResponse.get(resp.id) ?? []}
                    />
                  ))}
                </div>
              </details>
            </section>
          )}
        </>
      )}
    </div>
  );
}
