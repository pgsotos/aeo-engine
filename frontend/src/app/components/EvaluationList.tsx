"use client";

import { useState } from "react";
import type { Evaluation } from "../types";
import EvaluationListItem from "./EvaluationListItem";

interface EvaluationListProps {
  evaluations: Evaluation[];
  loading: boolean;
  selectedId: string | null;
  onOpen: (id: string) => void;
}

/**
 * The past-evaluations list.
 *
 * Which row is expanded is local state: it is a view preference nothing else
 * in the page reads, so it stays here rather than being lifted into the
 * container. One row expands at a time, which keeps the list scannable when
 * there are twenty of them.
 */
export default function EvaluationList({
  evaluations,
  loading,
  selectedId,
  onOpen,
}: EvaluationListProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-6">
      <h2 className="mb-4 text-lg font-semibold text-zinc-200">
        Past Evaluations
      </h2>

      {loading ? (
        <div className="py-8 text-center text-zinc-500">Loading…</div>
      ) : evaluations.length === 0 ? (
        <div className="py-8 text-center text-zinc-500">
          No evaluations yet. Configure above and click &quot;Run Evaluation&quot;.
        </div>
      ) : (
        <div className="space-y-2">
          {evaluations.map((ev) => (
            <EvaluationListItem
              key={ev.id}
              evaluation={ev}
              selected={selectedId === ev.id}
              expanded={expandedId === ev.id}
              onToggle={(id) => setExpandedId(expandedId === id ? null : id)}
              onOpen={onOpen}
            />
          ))}
        </div>
      )}
    </div>
  );
}
