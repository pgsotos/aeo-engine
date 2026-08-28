"use client";

import type { KeyboardEvent } from "react";
import type { UseEvaluationForm } from "../hooks/useEvaluationForm";
import Spinner from "./ui/Spinner";

interface NewEvaluationFormProps {
  form: UseEvaluationForm;
  running: boolean;
  onRun: () => void;
}

/**
 * The three-step evaluation setup: brand, then category, then competitors.
 *
 * Each control is disabled until the step above it resolves, so the sequence
 * is enforced by the form rather than explained in help text. The whole state
 * machine lives in `useEvaluationForm`; this renders it and nothing else.
 */
export default function NewEvaluationForm({
  form,
  running,
  onRun,
}: NewEvaluationFormProps) {
  const canRun = form.isReady && !running;

  function handleBrandKeyDown(e: KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      void form.resolveCategories();
    }
  }

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-6">
      <h2 className="mb-4 text-lg font-semibold text-zinc-200">New Evaluation</h2>

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
            Category
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
        </div>
      </div>

      <div className="mt-4">
        <label className="mb-1 block text-sm text-zinc-400">Competitors</label>
        <CompetitorField form={form} />
      </div>

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

/** The competitor slot, which is one of four mutually exclusive states. */
function CompetitorField({ form }: { form: UseEvaluationForm }) {
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
      <button
        type="button"
        onClick={() => void form.resolveCompetitors()}
        className="inline-flex items-center justify-center gap-2 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-300 transition-colors hover:bg-zinc-700"
      >
        Resolve Competitors
      </button>
    );
  }

  return <p className="text-sm text-zinc-500">Select a category first</p>;
}
