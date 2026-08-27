"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import ConfidenceBar from "./components/ConfidenceBar";
import Heatmap from "./components/Heatmap";
import ResponseCard from "./components/ResponseCard";
import {
  fetchEvaluationDetail,
  fetchEvaluations,
  runEvaluation,
} from "./api";
import type {
  ClassificationResult,
  DashboardData,
  Evaluation,
  MetricSummary,
  PromptType,
} from "./types";

const PROMPT_TYPES: PromptType[] = [
  "direct",
  "comparative",
  "use_case",
  "feature",
  "negative",
];

const STATUS_COLORS: Record<string, string> = {
  completed: "text-emerald-400",
  running: "text-yellow-400",
  pending: "text-zinc-400",
  failed: "text-red-400",
};

export default function DashboardPage() {
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loadingEvals, setLoadingEvals] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadEvaluations = useCallback(async () => {
    try {
      setLoadingEvals(true);
      const data = await fetchEvaluations();
      setEvaluations(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load evaluations");
    } finally {
      setLoadingEvals(false);
    }
  }, []);

  const loadDetail = useCallback(async (id: string) => {
    try {
      setLoadingDetail(true);
      setError(null);
      const data = await fetchEvaluationDetail(id);
      setDashboard(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load detail");
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setLoadingEvals(true);
        const data = await fetchEvaluations();
        if (!cancelled) setEvaluations(data);
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Failed to load evaluations");
      } finally {
        if (!cancelled) setLoadingEvals(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSelect = useCallback(
    (id: string) => {
      setSelectedId(id);
      void loadDetail(id);
    },
    [loadDetail],
  );

  const handleRun = useCallback(async () => {
    try {
      setRunning(true);
      setError(null);
      await runEvaluation();
      await loadEvaluations();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to run evaluation");
    } finally {
      setRunning(false);
    }
  }, [loadEvaluations]);

  const linearMetrics = useMemo(() => {
    if (!dashboard) return null;
    return dashboard.metrics.filter((m) => m.brand === "Linear");
  }, [dashboard]);

  const linearByType = useMemo(() => {
    if (!linearMetrics) return new Map<PromptType, MetricSummary>();
    const map = new Map<PromptType, MetricSummary>();
    for (const m of linearMetrics) map.set(m.prompt_type, m);
    return map;
  }, [linearMetrics]);

  const responseClassMap = useMemo(() => {
    if (!dashboard) return new Map<string, ClassificationResult[]>();
    const map = new Map<string, ClassificationResult[]>();
    for (const cls of dashboard.classifications) {
      const arr = map.get(cls.response_id) ?? [];
      arr.push(cls);
      map.set(cls.response_id, arr);
    }
    return map;
  }, [dashboard]);

  const evaluationList = useMemo(() => {
    return evaluations.map((ev) => ({
      ...ev,
      date: new Date(ev.created_at).toLocaleDateString(),
    }));
  }, [evaluations]);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              AEO Analytics Dashboard
            </h1>
            <p className="mt-1 text-sm text-zinc-400">
              How often is Linear the direct answer in Gemini?
            </p>
          </div>
          <button
            type="button"
            onClick={handleRun}
            disabled={running}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {running ? (
              <>
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Running Evaluation…
              </>
            ) : (
              "Run Evaluation"
            )}
          </button>
        </div>

        {error && (
          <div className="mb-6 rounded-lg border border-red-800/50 bg-red-900/20 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        {/* Evaluation selector */}
        {!dashboard && (
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-6">
            <h2 className="mb-4 text-lg font-semibold text-zinc-200">
              Evaluations
            </h2>
            {loadingEvals ? (
              <div className="py-8 text-center text-zinc-500">Loading…</div>
            ) : evaluations.length === 0 ? (
              <div className="py-8 text-center text-zinc-500">
                No evaluations yet. Click &quot;Run Evaluation&quot; to start one.
              </div>
            ) : (
              <div className="space-y-2">
                {evaluationList.map((ev) => (
                  <button
                    key={ev.id}
                    type="button"
                    onClick={() => handleSelect(ev.id)}
                    className={`flex w-full items-center justify-between rounded-lg border px-4 py-3 text-left transition-colors ${
                      selectedId === ev.id
                        ? "border-blue-600 bg-blue-900/20"
                        : "border-zinc-800 hover:border-zinc-700 hover:bg-zinc-800/50"
                    }`}
                  >
                    <div>
                      <span className="font-medium text-zinc-200">
                        {ev.brand}
                      </span>
                      <span className="ml-2 text-sm text-zinc-500">
                        {ev.category}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-sm">
                      <span className="text-zinc-500">{ev.date}</span>
                      <span className={STATUS_COLORS[ev.status] ?? "text-zinc-400"}>
                        {ev.status}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Dashboard view */}
        {dashboard && (
          <div className="space-y-8">
            {/* Back + info bar */}
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <button
                type="button"
                onClick={() => {
                  setDashboard(null);
                  setSelectedId(null);
                }}
                className="inline-flex items-center gap-1 text-sm text-zinc-400 transition-colors hover:text-zinc-200"
              >
                ← Back to list
              </button>
              <div className="flex flex-wrap items-center gap-4 text-sm text-zinc-400">
                <span>
                  Brand:{" "}
                  <span className="font-medium text-zinc-200">
                    {dashboard.evaluation.brand}
                  </span>
                </span>
                <span>
                  N = {dashboard.evaluation.sampling_n}
                </span>
                <span>
                  Status:{" "}
                  <span
                    className={
                      STATUS_COLORS[dashboard.evaluation.status] ?? "text-zinc-400"
                    }
                  >
                    {dashboard.evaluation.status}
                  </span>
                </span>
                <span>
                  {new Date(dashboard.evaluation.created_at).toLocaleString()}
                </span>
              </div>
            </div>

            {/* Heatmap */}
            {loadingDetail ? (
              <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 py-12 text-center text-zinc-500">
                Loading dashboard…
              </div>
            ) : (
              <>
                <section>
                  <h2 className="mb-4 text-lg font-semibold text-zinc-200">
                    Multi-Dimension Heatmap
                  </h2>
                  <Heatmap metrics={dashboard.metrics} />
                </section>

                {/* Confidence intervals for Linear */}
                {linearMetrics && linearMetrics.length > 0 && (
                  <section>
                    <h2 className="mb-4 text-lg font-semibold text-zinc-200">
                      Linear Win Rate by Prompt Type
                    </h2>
                    <div className="space-y-4 rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
                      {PROMPT_TYPES.map((type) => {
                        const m = linearByType.get(type);
                        if (!m) return null;
                        return <ConfidenceBar key={type} metric={m} />;
                      })}
                    </div>
                  </section>
                )}

                {/* Response cards */}
                {dashboard.responses.length > 0 && (
                  <section>
                    <h2 className="mb-4 text-lg font-semibold text-zinc-200">
                      Individual Responses ({dashboard.responses.length})
                    </h2>
                    <div className="space-y-3">
                      {dashboard.responses.map((resp) => (
                        <ResponseCard
                          key={resp.id}
                          response={resp}
                          classifications={
                            responseClassMap.get(resp.id) ?? []
                          }
                        />
                      ))}
                    </div>
                  </section>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
