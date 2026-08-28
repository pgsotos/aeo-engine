"use client";

import { statusColor } from "../constants";
import type { Evaluation } from "../types";

interface DashboardHeaderProps {
  evaluation: Evaluation;
  onBack: () => void;
}

/** Back link plus the parameters the numbers below were produced under. */
export default function DashboardHeader({
  evaluation,
  onBack,
}: DashboardHeaderProps) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <button
        type="button"
        onClick={onBack}
        className="inline-flex items-center gap-1 text-sm text-zinc-400 transition-colors hover:text-zinc-200"
      >
        ← Back to list
      </button>
      <div className="flex flex-wrap items-center gap-4 text-sm text-zinc-400">
        <span>
          Brand:{" "}
          <span className="font-medium text-zinc-200">{evaluation.brand}</span>
        </span>
        <span>
          Category:{" "}
          <span className="font-medium text-zinc-200">
            {evaluation.category}
          </span>
        </span>
        <span>N = {evaluation.sampling_n}</span>
        <span>
          Status:{" "}
          <span className={statusColor(evaluation.status)}>
            {evaluation.status}
          </span>
        </span>
      </div>
    </div>
  );
}
