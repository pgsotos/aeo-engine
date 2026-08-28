"use client";

import type { EvaluationInterpretation } from "../lib/interpret";
import { STRONG_THRESHOLD, WEAK_THRESHOLD } from "../lib/interpret";
import type { Evaluation } from "../types";
import { PROMPT_TYPE_LABELS } from "../types";

interface ExecutiveSummaryProps {
  interpretation: EvaluationInterpretation;
  evaluation: Evaluation;
}

const VERDICT: Record<
  EvaluationInterpretation["verdictTone"],
  { label: string; blurb: string; border: string }
> = {
  strong: {
    label: "Strong position",
    blurb:
      "typically the direct answer the model chooses. A competitor takes the slot only on specific angles.",
    border: "border-emerald-500/40",
  },
  contested: {
    label: "Contested position",
    blurb:
      "the model often mentions this brand but is not consistently choosing it as the direct answer.",
    border: "border-yellow-500/40",
  },
  weak: {
    label: "Weak position",
    blurb:
      "rarely surfaces as the direct answer; a competitor usually wins the slot.",
    border: "border-red-500/40",
  },
};

function pct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

export default function ExecutiveSummary({
  interpretation: i,
  evaluation,
}: ExecutiveSummaryProps) {
  const v = VERDICT[i.verdictTone];

  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold text-zinc-200">
        Executive Summary
      </h2>

      {/* Verdict + KPI chips */}
      <div className={`rounded-lg border ${v.border} bg-zinc-900/50 p-4`}>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="text-sm font-semibold uppercase tracking-wide text-zinc-400">
              {evaluation.brand} in “{evaluation.category}”
            </div>
            <p className="mt-2 text-base text-zinc-200">
              <span className="font-semibold">{v.label}.</span>{" "}
              {evaluation.brand} was the direct answer in{" "}
              <span className="font-medium text-zinc-100">
                {pct(i.focusWinRate)}
              </span>{" "}
              of queries across all prompt types
              {i.incomplete ? " (subset available)" : ""}, with a confidence
              interval of {pct(i.ciLower)}–{pct(i.ciUpper)}.
            </p>
            <p className="mt-1 text-sm text-zinc-400">{v.blurb}</p>
          </div>

          <div className="flex shrink-0 items-center gap-3">
            <div className="text-center">
              <div className="text-3xl font-bold text-zinc-100">
                {pct(i.focusWinRate)}
              </div>
              <div className="text-xs text-zinc-500">Direct answer</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-zinc-100">
                {evaluation.consistency == null
                  ? "—"
                  : `${pct(evaluation.consistency)}`}
              </div>
              <div className="text-xs text-zinc-500">Consistency</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-zinc-100">
                {evaluation.sampling_n}
              </div>
              <div className="text-xs text-zinc-500">Runs (N)</div>
            </div>
          </div>
        </div>
      </div>

      {/* Strengths / weaknesses */}
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
          <div className="mb-2 text-sm font-semibold text-emerald-300">
            Where it shines
          </div>
          {i.strengths.length === 0 ? (
            <p className="text-sm text-zinc-500">
              No prompt type exceeds {pct(STRONG_THRESHOLD)}.
            </p>
          ) : (
            <ul className="space-y-1 text-sm text-zinc-300">
              {i.strengths.map((s) => (
                <li key={s.type}>
                  <span className="font-medium text-zinc-200">
                    {PROMPT_TYPE_LABELS[s.type]}
                  </span>
                  : <span className="text-emerald-300">{pct(s.winRate)}</span>{" "}
                  direct answer
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
          <div className="mb-2 text-sm font-semibold text-red-300">
            Where it loses ground
          </div>
          {i.weaknesses.length === 0 ? (
            <p className="text-sm text-zinc-500">
              No prompt type falls below {pct(WEAK_THRESHOLD)}.
            </p>
          ) : (
            <ul className="space-y-1 text-sm text-zinc-300">
              {i.weaknesses.map((w) => (
                <li key={w.type}>
                  <span className="font-medium text-zinc-200">
                    {PROMPT_TYPE_LABELS[w.type]}
                  </span>
                  : only{" "}
                  <span className="text-red-300">{pct(w.winRate)}</span> direct
                  answer
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Competition */}
      {i.competitorsAhead.length > 0 && (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
          <div className="mb-2 text-sm font-semibold text-zinc-300">
            Competitors ahead
          </div>
          <ul className="space-y-1 text-sm text-zinc-400">
            {i.competitorsAhead.map((c) => (
              <li key={c.brand}>
                {c.brand} is ahead by{" "}
                <span className="font-medium text-zinc-200">
                  {c.delta} points
                </span>{" "}
                ({pct(c.winRate)} vs {pct(i.focusWinRate)}).
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
