"use client";

import type { KeyboardEvent } from "react";
import type { UseEvaluationForm } from "../hooks/useEvaluationForm";
import Spinner from "./ui/Spinner";

interface NewEvaluationFormProps {
  form: UseEvaluationForm;
  running: boolean;
  onRun: () => void;
}

/** One row in the step narrative; its state is derived from hook flags only. */
interface StepMeta {
  label: string;
  state: "complete" | "active" | "pending";
}

/** Build the 1 Brand → 2 Category → 3 Competitors narrative from existing flags. */
function buildSteps(form: UseEvaluationForm): StepMeta[] {
  const brandComplete = form.brand.trim() !== "";
  const categoryComplete = form.categories.length > 0;
  const competitorsComplete = form.competitorsResolved;

  return [
    { label: "Brand", state: brandComplete ? "complete" : "active" },
    {
      label: "Category",
      state: categoryComplete ? "complete" : brandComplete ? "active" : "pending",
    },
    {
      label: "Competitors",
      state: competitorsComplete ? "complete" : categoryComplete ? "active" : "pending",
    },
  ];
}

/**
 * The three-step evaluation setup: brand, then category, then competitors.
 *
 * Each step is resolved by Gemini, so the form explains that inference and asks
 * the user to verify before running. The narrative and inline errors are derived
 * entirely from `useEvaluationForm`'s rendered flags — no new state here.
 */
export default function NewEvaluationForm({
  form,
  running,
  onRun,
}: NewEvaluationFormProps) {
  const canRun = form.isReady && !running && !form.error;
  const steps = buildSteps(form);

  // Which step a pending inline error belongs to. A category resolve failure
  // leaves categories empty; a competitor resolve failure leaves them resolved.
  const categoryErrorMessage =
    form.error && form.categories.length === 0 ? form.error : null;
  const competitorErrorMessage =
    form.error && form.categories.length > 0 && !form.competitorsResolved
      ? form.error
      : null;

  function handleBrandKeyDown(e: KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      void form.resolveCategories();
    }
  }

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-6">
      <h2 className="mb-4 text-lg font-semibold text-zinc-200">New Evaluation</h2>

      <ol className="mb-5 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm" aria-label="Setup steps">
        {steps.map((step, index) => (
          <li
            key={step.label}
            className={`flex items-center gap-2 ${
              step.state === "active"
                ? "font-medium text-zinc-100"
                : step.state === "complete"
                  ? "text-zinc-400"
                  : "text-zinc-600"
            }`}
          >
            {index > 0 && <span className="text-zinc-600">→</span>}
            <span>
              <span className="mr-1 text-zinc-600">{index + 1}.</span>
              {step.label}
            </span>
          </li>
        ))}
      </ol>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="brand" className="mb-1 block text-sm text-zinc-400">
            Brand
          </label>
          <div className="flex gap-2">
            <input
              id="brand"
              type="text"
              value={form.brand}
              onChange={(e) => form.setBrand(e.target.value)}
              onBlur={() => void form.resolveCategories()}
              onKeyDown={handleBrandKeyDown}
              className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="e.g. Linear, Sony, Notion"
            />
            <button
              type="button"
              onClick={() => void form.resolveCategories()}
              disabled={form.resolvingCategories || !form.brand.trim()}
              className="inline-flex items-center justify-center rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-300 transition-colors hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {form.resolvingCategories ? <Spinner /> : "Resolve"}
            </button>
          </div>
        </div>

        <div>
          <label htmlFor="category" className="mb-1 block text-sm text-zinc-400">
            Categories for {form.resolvedBrand ?? form.brand}
          </label>
          {form.categories.length > 0 ? (
            <select
              id="category"
              value={form.category}
              onChange={(e) => form.setCategory(e.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="" disabled>
                Select a category…
              </option>
              {form.categories.map((cat) => (
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
              readOnly
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-500"
              placeholder={
                form.resolvingCategories
                  ? "Resolving categories…"
                  : "Enter a brand first"
              }
            />
          )}
          {categoryErrorMessage && (
            <InlineError
              message={categoryErrorMessage}
              onRetry={() => void form.resolveCategories()}
            />
          )}
        </div>
      </div>

      <div className="mt-4">
        <label className="mb-1 block text-sm text-zinc-400">Competitors</label>
        <CompetitorField form={form} competitorError={competitorErrorMessage} />
      </div>

      <p className="mt-4 max-w-xl text-xs leading-relaxed text-zinc-500">
        Categories and competitors are inferred by Gemini from your brand. Verify
        them before running an evaluation — a bad guess would skew the results.
      </p>

      <button
        type="button"
        onClick={onRun}
        disabled={!canRun}
        className="mt-5 inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {running ? (
          <>
            <Spinner />
            Running Evaluation…
          </>
        ) : (
          "Run Evaluation"
        )}
      </button>
    </div>
  );
}

/** An accessible inline step error with an obvious Retry for the failed resolve. */
function InlineError({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div
      role="alert"
      className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-red-400"
    >
      <span>{message}</span>
      <button
        type="button"
        onClick={onRetry}
        className="rounded-lg border border-zinc-700 bg-zinc-800 px-2.5 py-1 text-xs font-medium text-zinc-200 transition-colors hover:bg-zinc-700"
      >
        Retry
      </button>
    </div>
  );
}

/** The competitor slot, which is one of four mutually exclusive states. */
function CompetitorField({
  form,
  competitorError,
}: {
  form: UseEvaluationForm;
  competitorError: string | null;
}) {
  if (form.resolvingCompetitors) {
    return (
      <div className="flex items-center gap-2 text-sm text-zinc-500">
        <Spinner />
        Resolving competitors…
      </div>
    );
  }

  if (form.competitorsResolved && form.competitors.length > 0) {
    return (
      <div className="space-y-2">
        {form.competitors.map((c) => (
          <div key={c.name} className="flex items-start gap-2 text-sm">
            <span className="font-medium text-zinc-200">{c.name}</span>
            <span className="text-zinc-500">—</span>
            <span className="text-zinc-400">{c.reason}</span>
          </div>
        ))}
      </div>
    );
  }

  if (form.category) {
    return (
      <div>
        <button
          type="button"
          onClick={() => void form.resolveCompetitors()}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-300 transition-colors hover:bg-zinc-700"
        >
          Resolve Competitors
        </button>
        {competitorError && (
          <InlineError
            message={competitorError}
            onRetry={() => void form.resolveCompetitors()}
          />
        )}
      </div>
    );
  }

  return <p className="text-sm text-zinc-500">Select a category first</p>;
}
