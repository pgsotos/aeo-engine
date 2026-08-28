"use client";

import type { Evaluation } from "../types";

interface StartHereBannerProps {
  evaluation: Evaluation;
  onOpen: (id: string) => void;
}

/**
 * Entry point for a first-time visitor.
 *
 * A new arrival would otherwise face an empty dashboard behind a two-minute
 * run. Offering a finished evaluation up front means the first thing they see
 * is real data. Deliberately a button, not an auto-redirect: opening a page
 * that immediately navigates elsewhere reads as a bug.
 */
export default function StartHereBanner({
  evaluation,
  onOpen,
}: StartHereBannerProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-emerald-800/40 bg-emerald-900/15 px-5 py-4">
      <div className="text-sm text-zinc-300">
        <span className="font-medium text-emerald-300">Start here.</span> A
        finished evaluation is ready to explore — no need to run one first.
        Running a new one takes about two minutes.
      </div>
      <button
        type="button"
        onClick={() => onOpen(evaluation.id)}
        className="shrink-0 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
      >
        View {evaluation.brand} results →
      </button>
    </div>
  );
}
