"use client";

import { useMemo } from "react";
import type { ClassificationResult, GeminiResponse } from "../types";
import { BRANDS } from "../types";

interface ResponseCardProps {
  response: GeminiResponse;
  classifications: ClassificationResult[];
}

const CLASSIFICATION_STYLES: Record<string, string> = {
  direct_winner:
    "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  alternative_mention:
    "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  omitted: "bg-red-500/20 text-red-300 border-red-500/30",
};

const CLASSIFICATION_LABELS: Record<string, string> = {
  direct_winner: "Direct Winner",
  alternative_mention: "Alternative",
  omitted: "Omitted",
};

function highlightBrands(
  text: string,
  brandClassifications: Map<string, ClassificationResult>,
): React.ReactNode[] {
  const brandPositions: Array<{
    brand: string;
    start: number;
    end: number;
  }> = [];

  for (const brand of BRANDS) {
    const lowerText = text.toLowerCase();
    const lowerBrand = brand.toLowerCase();
    let searchStart = 0;

    while (searchStart < lowerText.length) {
      const idx = lowerText.indexOf(lowerBrand, searchStart);
      if (idx === -1) break;
      brandPositions.push({ brand, start: idx, end: idx + brand.length });
      searchStart = idx + 1;
    }
  }

  brandPositions.sort((a, b) => a.start - b.start);

  const nodes: React.ReactNode[] = [];
  let cursor = 0;

  const brandUnderlineColor: Record<string, string> = {
    Linear: "border-b-blue-400",
    Jira: "border-b-blue-300",
    Asana: "border-b-purple-400",
    Monday: "border-b-orange-400",
    Notion: "border-b-zinc-300",
  };

  for (const pos of brandPositions) {
    if (pos.start < cursor) continue;

    if (pos.start > cursor) {
      nodes.push(
        <span key={`t-${cursor}`}>{text.slice(cursor, pos.start)}</span>,
      );
    }

    const cls = brandClassifications.get(pos.brand);
    const badge =
      cls?.classification === "direct_winner"
        ? "★"
        : cls?.classification === "alternative_mention"
          ? "◆"
          : "";

    nodes.push(
      <span
        key={`b-${pos.start}-${pos.brand}`}
        className={`font-semibold border-b-2 ${brandUnderlineColor[pos.brand] ?? "border-b-zinc-400"}`}
      >
        {text.slice(pos.start, pos.end)}
        {badge && (
          <span className="ml-0.5 text-[10px] opacity-60">{badge}</span>
        )}
      </span>,
    );

    cursor = pos.end;
  }

  if (cursor < text.length) {
    nodes.push(<span key="rest">{text.slice(cursor)}</span>);
  }

  return nodes.length > 0 ? nodes : [text];
}

export default function ResponseCard({
  response,
  classifications,
}: ResponseCardProps) {
  const brandClassMap = useMemo(() => {
    const map = new Map<string, ClassificationResult>();
    for (const c of classifications) {
      if (c.response_id === response.id) {
        map.set(c.brand, c);
      }
    }
    return map;
  }, [classifications, response.id]);

  const date = new Date(response.created_at);
  const formatted = date.toLocaleString();

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-zinc-500">
        <span>Prompt: {response.prompt_id}</span>
        <span className="text-zinc-700">·</span>
        <span>Run {response.run_index}</span>
        <span className="text-zinc-700">·</span>
        <span>{response.model_id}</span>
        <span className="text-zinc-700">·</span>
        <span>{formatted}</span>
      </div>

      <div className="mb-3 text-sm leading-relaxed text-zinc-300 whitespace-pre-wrap">
        {highlightBrands(response.raw_text, brandClassMap)}
      </div>

      <div className="flex flex-wrap gap-2">
        {[...brandClassMap.values()].map((cls) => (
          <span
            key={cls.brand}
            className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${CLASSIFICATION_STYLES[cls.classification] ?? "bg-zinc-800 text-zinc-400 border-zinc-700"}`}
          >
            {cls.brand}: {CLASSIFICATION_LABELS[cls.classification] ?? cls.classification}
            {cls.mention_count > 0 && (
              <span className="opacity-60">({cls.mention_count})</span>
            )}
            {cls.first_mention_position !== null &&
              cls.first_mention_position > 0 && (
                <span className="opacity-40">
                  @{cls.first_mention_position}
                </span>
              )}
          </span>
        ))}
      </div>
    </div>
  );
}
