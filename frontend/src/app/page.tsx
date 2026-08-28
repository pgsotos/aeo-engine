"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import BackendStatus from "./components/BackendStatus";
import ConfidenceBar from "./components/ConfidenceBar";
import Heatmap from "./components/Heatmap";
import ResponseCard from "./components/ResponseCard";
import {
  fetchCategories,
  fetchCompetitors,
  fetchEvaluationDetail,
  fetchEvaluations,
  runEvaluation,
} from "./api";
import type {
  ClassificationResult,
  Competitor,
  DashboardData,
  Evaluation,
  EvaluateRequest,
  MetricSummary,
  PromptType,
} from "./types";
import { useBackendHealth } from "./hooks/useBackendHealth";

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

  // Evaluation form state
  const [brand, setBrand] = useState("");
  const [category, setCategory] = useState("");
  const [categories, setCategories] = useState<string[]>([]);
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [resolvingCategories, setResolvingCategories] = useState(false);
  const [resolvingCompetitors, setResolvingCompetitors] = useState(false);
  const [resolvedBrand, setResolvedBrand] = useState<string | null>(null);
  const [competitorsResolved, setCompetitorsResolved] = useState(false);

  const backendHealth = useBackendHealth();

  // Set once on unmount so the long-running poll in `handleRun` can bail out
  // instead of calling setState on a torn-down component.
  const cancelledRef = useRef(false);
  useEffect(() => {
    return () => {
      cancelledRef.current = true;
    };
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
        if (cancelled) return;
        setEvaluations(data);
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

  const handleResolveCategories = useCallback(async () => {
    const trimmed = brand.trim();
    if (!trimmed) return;
    if (resolvedBrand === trimmed && categories.length > 0) return;

    try {
      setResolvingCategories(true);
      setError(null);
      setCategory("");
      setCompetitors([]);
      setCompetitorsResolved(false);
      const data = await fetchCategories(trimmed);
      setCategories(data.categories);
      setResolvedBrand(trimmed);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Failed to resolve categories",
      );
      setCategories([]);
      setResolvedBrand(null);
    } finally {
      setResolvingCategories(false);
    }
  }, [brand, resolvedBrand, categories.length]);

  const handleResolveCompetitors = useCallback(async () => {
    if (!category || !resolvedBrand) return;

    try {
      setResolvingCompetitors(true);
      setError(null);
      const data = await fetchCompetitors(resolvedBrand, category);
      setCompetitors(data.competitors);
      setCompetitorsResolved(true);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Failed to resolve competitors",
      );
      setCompetitors([]);
      setCompetitorsResolved(false);
    } finally {
      setResolvingCompetitors(false);
    }
  }, [category, resolvedBrand]);

  const handleBrandKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        void handleResolveCategories();
      }
    },
    [handleResolveCategories],
  );

  const canRun = useMemo(() => {
    return (
      brand.trim() !== "" &&
      category !== "" &&
      competitorsResolved &&
      competitors.length > 0 &&
      !running &&
      !resolvingCategories &&
      !resolvingCompetitors
    );
  }, [brand, category, competitorsResolved, competitors.length, running, resolvingCategories, resolvingCompetitors]);

  const handleRun = useCallback(async () => {
    if (!brand.trim() || !category || competitors.length === 0) {
      setError("All fields are required");
      return;
    }

    const request: EvaluateRequest = {
      brand: brand.trim(),
      category,
      competitors: competitors.map((c) => c.name),
    };

    try {
      setRunning(true);
      setError(null);
      // The backend runs the evaluation in the background and returns
      // immediately; poll the list until this run finishes.
      const { evaluation_id } = await runEvaluation(request);
      if (cancelledRef.current) return;

      const deadline = Date.now() + 15 * 60_000;
      let consecutiveFailures = 0;
      const MAX_CONSECUTIVE_FAILURES = 5;

      while (Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, 5_000));
        if (cancelledRef.current) return;

        let evals: Evaluation[];
        try {
          evals = await fetchEvaluations();
          consecutiveFailures = 0;
        } catch {
          // Render's free tier cold-starts and blips; tolerate a few
          // transient failures before giving up on the poll.
          consecutiveFailures += 1;
          if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
            if (!cancelledRef.current)
              setError(
                "Lost connection to the backend while polling; the run may still finish — check back later.",
              );
            return;
          }
          continue;
        }

        if (cancelledRef.current) return;
        setEvaluations(evals);

        const mine = evals.find((e) => e.id === evaluation_id);
        if (mine && mine.status !== "running" && mine.status !== "pending") {
          if (mine.status === "completed") {
            setSelectedId(evaluation_id);
            await loadDetail(evaluation_id);
          } else {
            setError("Evaluation failed — check the backend logs.");
          }
          return;
        }
      }
      if (!cancelledRef.current)
        setError("Evaluation is taking longer than expected; check back later.");
    } catch (e) {
      if (!cancelledRef.current)
        setError(e instanceof Error ? e.message : "Failed to run evaluation");
    } finally {
      if (!cancelledRef.current) setRunning(false);
    }
  }, [brand, category, competitors, loadDetail]);

  // Metrics for the focus brand
  const focusMetrics = useMemo(() => {
    if (!dashboard) return null;
    return dashboard.metrics.filter(
      (m) => m.brand === dashboard.evaluation.brand,
    );
  }, [dashboard]);

  const focusByType = useMemo(() => {
    if (!focusMetrics) return new Map<PromptType, MetricSummary>();
    const map = new Map<PromptType, MetricSummary>();
    for (const m of focusMetrics) map.set(m.prompt_type, m);
    return map;
  }, [focusMetrics]);

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

  // The list arrives most-recent-first, so the first finished run is the
  // freshest one — offered up front so a first-time visitor can see real
  // results without waiting for an evaluation to run.
  const latestCompleted = useMemo(
    () => evaluations.find((ev) => ev.status === "completed") ?? null,
    [evaluations],
  );

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold tracking-tight text-white">
            AEO Analytics Dashboard
          </h1>
          <p className="mt-1 text-sm text-zinc-400">
            Measure how often a brand is the direct answer in any AI engine.
          </p>
        </div>

        {error && (
          <div className="mb-6 rounded-lg border border-red-800/50 bg-red-900/20 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        <BackendStatus health={backendHealth} />

        {/* Evaluation selector + form */}
        {!dashboard && (
          <div className="space-y-6">
            {/* Start here: open a finished evaluation without waiting for a run */}
            {latestCompleted && (
              <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-emerald-800/40 bg-emerald-900/15 px-5 py-4">
                <div className="text-sm text-zinc-300">
                  <span className="font-medium text-emerald-300">
                    Start here.
                  </span>{" "}
                  A finished evaluation is ready to explore — no need to run one
                  first. Running a new one takes about two minutes.
                </div>
                <button
                  type="button"
                  onClick={() => handleSelect(latestCompleted.id)}
                  className="shrink-0 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
                >
                  View {latestCompleted.brand} results →
                </button>
              </div>
            )}

            {/* New evaluation form */}
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-6">
              <h2 className="mb-4 text-lg font-semibold text-zinc-200">
                New Evaluation
              </h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {/* Brand input */}
                <div>
                  <label htmlFor="brand" className="mb-1 block text-sm text-zinc-400">
                    Brand
                  </label>
                  <div className="flex gap-2">
                    <input
                      id="brand"
                      type="text"
                      value={brand}
                      onChange={(e) => {
                        setBrand(e.target.value);
                        if (e.target.value !== resolvedBrand) {
                          setCategories([]);
                          setCategory("");
                          setCompetitors([]);
                          setResolvedBrand(null);
                        }
                      }}
                      onBlur={handleResolveCategories}
                      onKeyDown={handleBrandKeyDown}
                      className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      placeholder="e.g. Linear, Sony, Notion"
                    />
                    <button
                      type="button"
                      onClick={handleResolveCategories}
                      disabled={resolvingCategories || !brand.trim()}
                      className="inline-flex items-center justify-center rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-300 transition-colors hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {resolvingCategories ? (
                        <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                      ) : (
                        "Resolve"
                      )}
                    </button>
                  </div>
                </div>

                {/* Category — select from resolved list */}
                <div>
                  <label htmlFor="category" className="mb-1 block text-sm text-zinc-400">
                    Category
                  </label>
                  {categories.length > 0 ? (
                    <select
                      id="category"
                      value={category}
                      onChange={(e) => {
                        setCategory(e.target.value);
                        setCompetitors([]);
                        setCompetitorsResolved(false);
                      }}
                      className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    >
                      <option value="" disabled>
                        Select a category…
                      </option>
                      {categories.map((cat) => (
                        <option key={cat} value={cat}>
                          {cat}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      id="category"
                      type="text"
                      disabled
                      value=""
                      className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-500"
                      placeholder={
                        resolvingCategories
                          ? "Resolving categories…"
                          : "Enter a brand first"
                      }
                    />
                  )}
                </div>
              </div>

              {/* Competitors — manual resolution */}
              <div className="mt-4">
                <label className="mb-1 block text-sm text-zinc-400">
                  Competitors
                </label>
                {resolvingCompetitors ? (
                  <div className="flex items-center gap-2 text-sm text-zinc-500">
                    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Resolving competitors…
                  </div>
                ) : competitorsResolved && competitors.length > 0 ? (
                  <div className="space-y-2">
                    {competitors.map((c) => (
                      <div
                        key={c.name}
                        className="flex items-start gap-2 text-sm"
                      >
                        <span className="font-medium text-zinc-200">
                          {c.name}
                        </span>
                        <span className="text-zinc-500">—</span>
                        <span className="text-zinc-400">{c.reason}</span>
                      </div>
                    ))}
                  </div>
                ) : category ? (
                  <button
                    type="button"
                    onClick={handleResolveCompetitors}
                    className="inline-flex items-center justify-center gap-2 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-300 transition-colors hover:bg-zinc-700"
                  >
                    Resolve Competitors
                  </button>
                ) : (
                  <p className="text-sm text-zinc-500">
                    Select a category first
                  </p>
                )}
              </div>

              <button
                type="button"
                onClick={handleRun}
                disabled={!canRun}
                className="mt-5 inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
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

            {/* Existing evaluations */}
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-6">
              <h2 className="mb-4 text-lg font-semibold text-zinc-200">
                Past Evaluations
              </h2>
              {loadingEvals ? (
                <div className="py-8 text-center text-zinc-500">Loading…</div>
              ) : evaluations.length === 0 ? (
                <div className="py-8 text-center text-zinc-500">
                  No evaluations yet. Configure above and click &quot;Run Evaluation&quot;.
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
                  Category:{" "}
                  <span className="font-medium text-zinc-200">
                    {dashboard.evaluation.category}
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
              </div>
            </div>

            {/* Legend / how to read this */}
            <details className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4 text-sm text-zinc-400">
              <summary className="cursor-pointer font-medium text-zinc-300">
                How to read this dashboard
              </summary>
              <div className="mt-3 space-y-2 leading-relaxed">
                <p>
                  Every answer is classified for each brand:{" "}
                  <span className="text-emerald-300">direct winner</span> (the
                  brand is the #1 recommendation),{" "}
                  <span className="text-yellow-300">alternative mention</span>{" "}
                  (secondary option or one item in a list), or{" "}
                  <span className="text-red-300">omitted</span> (absent — a
                  competitor takes the direct answer). In the response text,{" "}
                  <span className="text-zinc-200">★</span> marks a direct-winner
                  mention and <span className="text-zinc-200">◆</span> an
                  alternative mention.
                </p>
                <p>
                  <span className="font-medium text-zinc-300">Win Rate</span> is
                  the share of runs classified as{" "}
                  <span className="text-emerald-300">direct winner</span>. The{" "}
                  <span className="font-medium text-zinc-300">
                    Wilson score confidence interval
                  </span>{" "}
                  is the 95% uncertainty band around that rate for the sample
                  size — a wide band means we have not sampled enough to be
                  confident.
                </p>
                <p>
                  Each prompt type uses 2 base questions × 2 brand orderings
                  (inverted pairs, to cancel position bias) = 4 prompts, each
                  sampled N = {dashboard.evaluation.sampling_n} times. That is{" "}
                  {4 * dashboard.evaluation.sampling_n} runs per prompt type per
                  brand (shown as &quot;runs&quot; in each heatmap cell).
                </p>
              </div>
            </details>

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

                {/* Confidence intervals for focus brand */}
                {focusMetrics && focusMetrics.length > 0 && (
                  <section>
                    <h2 className="mb-4 text-lg font-semibold text-zinc-200">
                      {dashboard.evaluation.brand} Win Rate by Prompt Type
                    </h2>
                    <div className="space-y-4 rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
                      {PROMPT_TYPES.map((type) => {
                        const m = focusByType.get(type);
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
