"use client";

import type { SourceImpactRow } from "../types";

interface SourceAuditorProps {
  rows: SourceImpactRow[];
}

function renderImpact(impactRatio: number): string {
  return `${(impactRatio * 100).toFixed(0)}%`;
}

export default function SourceAuditor({ rows }: SourceAuditorProps) {
  return (
    <div className="space-y-3 rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
      {rows.length === 0 ? (
        <p className="text-sm text-zinc-500">
          No grounding captured for this evaluation
        </p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 text-left text-xs uppercase tracking-wide text-zinc-500">
              <th className="py-2 pr-4 font-medium">Source Domain</th>
              <th className="py-2 pr-4 font-medium">Citations</th>
              <th className="py-2 pr-4 font-medium">Direct Wins</th>
              <th className="py-2 font-medium">Impact Ratio</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.domain}
                className="border-b border-zinc-800/60 last:border-0"
              >
                <td className="py-2 pr-4 text-zinc-200">{row.domain}</td>
                <td className="py-2 pr-4 text-zinc-400">{row.citations}</td>
                <td className="py-2 pr-4 text-zinc-400">{row.direct_wins}</td>
                <td className="py-2 text-zinc-300">
                  {renderImpact(row.impact_ratio)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
