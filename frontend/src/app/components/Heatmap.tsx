"use client";

import type { MetricSummary, PromptType } from "../types";
import { BRANDS, PROMPT_TYPE_LABELS } from "../types";

interface HeatmapProps {
  metrics: MetricSummary[];
}

function winRateColor(rate: number): string {
  if (rate >= 60) return "bg-emerald-500/20 text-emerald-300";
  if (rate >= 40) return "bg-yellow-500/20 text-yellow-300";
  return "bg-red-500/20 text-red-300";
}

function winRateBgBar(rate: number): string {
  if (rate >= 60) return "bg-emerald-500";
  if (rate >= 40) return "bg-yellow-500";
  return "bg-red-500";
}

const PROMPT_TYPES: PromptType[] = [
  "direct",
  "comparative",
  "use_case",
  "feature",
  "negative",
];

export default function Heatmap({ metrics }: HeatmapProps) {
  const cellMap = new Map<string, MetricSummary>();
  for (const m of metrics) {
    cellMap.set(`${m.prompt_type}-${m.brand}`, m);
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-800">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-800">
            <th className="px-4 py-3 text-left font-medium text-zinc-400">
              Prompt Type
            </th>
            {BRANDS.map((brand) => (
              <th
                key={brand}
                className="px-4 py-3 text-center font-medium text-zinc-400"
              >
                {brand}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {PROMPT_TYPES.map((type) => (
            <tr key={type} className="border-b border-zinc-800/50">
              <td className="px-4 py-3 font-medium text-zinc-200">
                {PROMPT_TYPE_LABELS[type]}
              </td>
              {BRANDS.map((brand) => {
                const cell = cellMap.get(`${type}-${brand}`);
                if (!cell) {
                  return (
                    <td
                      key={brand}
                      className="px-4 py-3 text-center text-zinc-600"
                    >
                      —
                    </td>
                  );
                }

                const pct = (cell.win_rate * 100).toFixed(1);
                const ciLow = (cell.ci_lower * 100).toFixed(1);
                const ciHigh = (cell.ci_upper * 100).toFixed(1);

                return (
                  <td key={brand} className="px-4 py-3">
                    <div
                      className={`rounded-md px-3 py-2 text-center ${winRateColor(cell.win_rate)}`}
                    >
                      <div className="text-lg font-semibold">{pct}%</div>
                      <div className="mt-0.5 text-xs opacity-70">
                        CI: {ciLow}%–{ciHigh}%
                      </div>
                      <div className="mt-1.5 mx-auto h-1 w-full max-w-[80px] overflow-hidden rounded-full bg-zinc-800">
                        <div
                          className={`h-full rounded-full ${winRateBgBar(cell.win_rate)}`}
                          style={{ width: `${cell.win_rate * 100}%` }}
                        />
                      </div>
                      <div className="mt-1 text-[10px] opacity-50">
                        {cell.total_runs} runs
                      </div>
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
