"use client";

interface DashboardLegendProps {
  samplingN: number;
}

/**
 * "How to read this dashboard", collapsed by default.
 *
 * The numbers here are derived, not restated: the runs-per-cell figure is
 * computed from the evaluation's own N, so it cannot drift out of sync with
 * what the heatmap actually counted.
 */
export default function DashboardLegend({ samplingN }: DashboardLegendProps) {
  const promptsPerType = 4; // 2 base questions x 2 brand orderings (ADR-024)

  return (
    <details className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4 text-sm text-zinc-400">
      <summary className="cursor-pointer font-medium text-zinc-300">
        How to read this dashboard
      </summary>
      <div className="mt-3 space-y-2 leading-relaxed">
        <p>
          Every answer is classified for each brand:{" "}
          <span className="text-emerald-300">direct winner</span> (the brand is
          the #1 recommendation),{" "}
          <span className="text-yellow-300">alternative mention</span>{" "}
          (secondary option or one item in a list), or{" "}
          <span className="text-red-300">omitted</span> (absent — a competitor
          takes the direct answer). In the response text,{" "}
          <span className="text-zinc-200">★</span> marks a direct-winner mention
          and <span className="text-zinc-200">◆</span> an alternative mention.
        </p>
        <p>
          <span className="font-medium text-zinc-300">Win Rate</span> is the
          share of runs classified as{" "}
          <span className="text-emerald-300">direct winner</span>. The{" "}
          <span className="font-medium text-zinc-300">
            Wilson score confidence interval
          </span>{" "}
          is the 95% uncertainty band around that rate for the sample size — a
          wide band means we have not sampled enough to be confident.
        </p>
        <p>
          Each prompt type uses 2 base questions × 2 brand orderings (inverted
          pairs, to cancel position bias) = {promptsPerType} prompts, each
          sampled N = {samplingN} times. That is {promptsPerType * samplingN}{" "}
          runs per prompt type per brand (shown as &quot;runs&quot; in each
          heatmap cell).
        </p>
      </div>
    </details>
  );
}
