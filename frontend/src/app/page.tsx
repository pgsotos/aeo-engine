"use client";

import { useCallback } from "react";
import BackendStatus from "./components/BackendStatus";
import EvaluationDashboard from "./components/EvaluationDashboard";
import EvaluationList from "./components/EvaluationList";
import NewEvaluationForm from "./components/NewEvaluationForm";
import StartHereBanner from "./components/StartHereBanner";
import ErrorBanner from "./components/ui/ErrorBanner";
import { useBackendHealth } from "./hooks/useBackendHealth";
import { useEvaluationDetail } from "./hooks/useEvaluationDetail";
import { useEvaluationForm } from "./hooks/useEvaluationForm";
import { useEvaluationRunner } from "./hooks/useEvaluationRunner";
import { useEvaluations } from "./hooks/useEvaluations";

/**
 * The dashboard container.
 *
 * Owns no state of its own: it wires four independent hooks to the two views
 * (list and results) and decides which one is showing. Anything with its own
 * lifecycle — the list, the open evaluation, the setup form, the run poller —
 * lives in a hook, and anything that renders lives in a component.
 */
export default function DashboardPage() {
  const health = useBackendHealth();
  const list = useEvaluations();
  const detail = useEvaluationDetail();
  const form = useEvaluationForm();

  const runner = useEvaluationRunner({
    onEvaluationsUpdated: list.replaceAll,
    onCompleted: detail.select,
  });

  const handleRun = useCallback(() => {
    const request = form.buildRequest();
    if (!request) return;
    void runner.run(request);
  }, [form, runner]);

  // One error surface, fed by whichever non-form concern failed. Detail first:
  // it is the most recent thing the user asked for when several can fail at
  // once. Form resolve errors render inline at their step in the form instead
  // of duplicating here.
  const error = detail.error ?? runner.error ?? list.error;

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-8">
          <h1 className="text-2xl font-bold tracking-tight text-white">
            AEO Analytics Dashboard
          </h1>
          <p className="mt-1 text-sm text-zinc-400">
            Measure how often a brand is the direct answer in any AI engine.
          </p>
        </header>

        <ErrorBanner message={error} />
        <BackendStatus health={health} />

        {detail.dashboard ? (
          <EvaluationDashboard
            dashboard={detail.dashboard}
            loading={detail.loading}
            onBack={detail.clear}
          />
        ) : (
          <div className="space-y-6">
            {list.latestCompleted && (
              <StartHereBanner
                evaluation={list.latestCompleted}
                onOpen={detail.select}
              />
            )}

            <NewEvaluationForm
              form={form}
              running={runner.running}
              onRun={handleRun}
            />

            <EvaluationList
              evaluations={list.evaluations}
              loading={list.loading}
              selectedId={detail.selectedId}
              onOpen={detail.select}
            />
          </div>
        )}
      </div>
    </div>
  );
}
