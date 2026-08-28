"use client";

import type { MetricSummary } from "../types";
import { PROMPT_TYPE_LABELS } from "../types";

interface ConfidenceBarProps {
  metric: MetricSummary;
}

function colorClass(ciLower: number, ciUpper: number): string {
  if (ciLower > 0.5) return "bg-emerald-500";
  if (ciUpper < 0.5) return "bg-red-500";
  return "bg-yellow-500";
}

function labelColor(ciLower: number, ciUpper: number): string {
  if (ciLower > 0.5) return "text-emerald-400";
  if (ciUpper < 0.5) return "text-red-400";
  return "text-yellow-400";
}

export default function ConfidenceBar({ metric }: ConfidenceBarProps) {
  const winPct = metric.win_rate * 100;
  const ciLowPct = metric.ci_lower * 100;
  const ciHighPct = metric.ci_upper * 100;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-zinc-300">
          {PROMPT_TYPE_LABELS[metric.prompt_type]}
        </span>
        <span className={`text-sm font-semibold ${labelColor(metric.ci_lower, metric.ci_upper)}`}>
          Win Rate: {winPct.toFixed(1)}% (CI: {ciLowPct.toFixed(1)}% – {ciHighPct.toFixed(1)}%)
        </span>
      </div>

      <div className="relative h-6 w-full rounded-full bg-zinc-800">
        {/* 50% reference line */}
        <div className="absolute left-1/2 top-0 h-full w-px bg-zinc-600" />

        {/* Win rate bar */}
        <div
          className={`absolute left-0 top-0 h-full rounded-full ${colorClass(metric.ci_lower, metric.ci_upper)}`}
          style={{ width: `${winPct}%` }}
        />

        {/* CI error bars */}
        <div
          className="absolute top-1/2 h-3 w-0.5 -translate-y-1/2 bg-white/80"
          style={{ left: `${ciLowPct}%` }}
        />
        <div
          className="absolute top-1/2 h-3 w-0.5 -translate-y-1/2 bg-white/80"
          style={{ left: `${ciHighPct}%` }}
        />
        {/* CI connector line */}
        <div
          className="absolute top-1/2 h-0.5 -translate-y-1/2 bg-white/30"
          style={{
            left: `${ciLowPct}%`,
            width: `${ciHighPct - ciLowPct}%`,
          }}
        />
      </div>

      <div className="text-xs text-zinc-500">
        {metric.direct_wins} direct wins · {metric.alternative_mentions} alternatives · {metric.omitted} omitted · {metric.total_runs} total runs
      </div>

      {/* Share of Voice — complementary to DWR */}
      <div className="space-y-1 pt-1">
        <div className="flex items-center justify-between text-xs">
          <span className="text-zinc-500">Share of Voice</span>
          <span className="font-medium text-zinc-400">
            {metric.share_of_voice == null
              ? "—"
              : `${(metric.share_of_voice * 100).toFixed(1)}%`}
          </span>
        </div>
        <div className="relative h-1.5 w-full rounded-full bg-zinc-800/70">
          <div
            className="absolute left-0 top-0 h-full rounded-full bg-sky-500/70"
            style={{
              width: `${(metric.share_of_voice ?? 0) * 100}%`,
            }}
          />
        </div>
      </div>
    </div>
  );
}
