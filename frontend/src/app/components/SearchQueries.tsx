"use client";

import type { SearchQueryRow } from "../types";

interface SearchQueriesProps {
  rows: SearchQueryRow[];
}

/**
 * What the engine actually searched for.
 *
 * Every other panel measures the answer. This one measures the step before it:
 * the queries Gemini ran against Google Search before writing anything. That
 * is the layer AEO work can act on — you cannot rewrite the model, but you can
 * be the page that ranks for the query it reaches for.
 *
 * The bar is scaled to the most frequent query rather than to the run count,
 * because the interesting comparison is between queries, not against a total
 * nobody has in mind.
 */
export default function SearchQueries({ rows }: SearchQueriesProps) {
  if (rows.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
        <p className="text-sm text-zinc-500">
          No searches recorded — the engine answered from its own knowledge for
          every run in this evaluation.
        </p>
      </div>
    );
  }

  const max = Math.max(...rows.map((r) => r.count));

  return (
    <div className="space-y-3 rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
      <p className="text-sm text-zinc-400">
        {rows.length} distinct {rows.length === 1 ? "query" : "queries"} run
        across this evaluation, most frequent first.
      </p>
      <ul className="space-y-2">
        {rows.map((row) => (
          <li key={row.query} className="space-y-1">
            <div className="flex items-baseline justify-between gap-4">
              <span className="font-mono text-sm text-zinc-200">
                {row.query}
              </span>
              <span className="shrink-0 text-xs tabular-nums text-zinc-500">
                {row.count}×
              </span>
            </div>
            <div
              className="h-1 rounded-full bg-zinc-800"
              role="presentation"
            >
              <div
                className="h-1 rounded-full bg-blue-500/70"
                style={{ width: `${(row.count / max) * 100}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
