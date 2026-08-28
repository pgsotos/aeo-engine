"use client";

import { statusColor } from "../constants";
import type { Evaluation } from "../types";

interface EvaluationListItemProps {
  evaluation: Evaluation;
  selected: boolean;
  expanded: boolean;
  onToggle: (id: string) => void;
  onOpen: (id: string) => void;
}

/**
 * One row in the past-evaluations list.
 *
 * Collapsed it shows identity and status; expanded it shows the competitor set
 * the run was scored against. The two actions are deliberately separate —
 * expanding to see who a brand was measured against is cheap, opening the
 * dashboard costs a fetch — so the row header toggles and only the explicit
 * button navigates.
 */
export default function EvaluationListItem({
  evaluation,
  selected,
  expanded,
  onToggle,
  onOpen,
}: EvaluationListItemProps) {
  const date = new Date(evaluation.created_at).toLocaleDateString();

  const borderClass = selected
    ? "border-blue-600 bg-blue-900/20"
    : expanded
      ? "border-zinc-700 bg-zinc-800/40"
      : "border-zinc-800 hover:border-zinc-700 hover:bg-zinc-800/50";

  return (
    <div className={`rounded-lg border transition-colors ${borderClass}`}>
      <button
        type="button"
        onClick={() => onToggle(evaluation.id)}
        aria-expanded={expanded}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <div className="flex items-center gap-2">
          <span
            aria-hidden
            className={`text-zinc-500 transition-transform ${expanded ? "rotate-90" : ""}`}
          >
            ▸
          </span>
          <span className="font-medium text-zinc-200">{evaluation.brand}</span>
          <span className="text-sm text-zinc-500">{evaluation.category}</span>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-zinc-500">{date}</span>
          <span className={statusColor(evaluation.status)}>
            {evaluation.status}
          </span>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-zinc-800 px-4 py-3">
          <div className="mb-3 text-sm">
            <span className="text-zinc-500">Scored against: </span>
            {evaluation.competitors && evaluation.competitors.length > 0 ? (
              <span className="text-zinc-300">
                {evaluation.competitors.join(" · ")}
              </span>
            ) : (
              <span className="text-zinc-500">
                {evaluation.status === "completed"
                  ? "no competitors recorded"
                  : "not scored yet"}
              </span>
            )}
          </div>
          <div className="flex items-center gap-4 text-sm text-zinc-500">
            <span>N = {evaluation.sampling_n} per prompt</span>
            <button
              type="button"
              onClick={() => onOpen(evaluation.id)}
              className="rounded-md bg-zinc-700 px-3 py-1.5 font-medium text-zinc-100 transition-colors hover:bg-zinc-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-400"
            >
              View results →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
