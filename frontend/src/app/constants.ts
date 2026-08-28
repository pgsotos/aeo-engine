import type { PromptType } from "./types";

/**
 * The five prompt dimensions, in the order they are displayed.
 *
 * Order is meaningful: it runs from the broadest question ("what is the best
 * tool?") to the most adversarial ("why should I *not* use it?"), so a reader
 * scanning a row sees the brand's position degrade or hold across framings.
 * The set itself is fixed by ADR-024 — adding one changes the denominator and
 * makes results incomparable with earlier runs.
 */
export const PROMPT_TYPES: PromptType[] = [
  "direct",
  "comparative",
  "use_case",
  "feature",
  "negative",
];

/** Evaluation lifecycle states, mapped to the colour that carries their tone. */
export const STATUS_COLORS: Record<string, string> = {
  completed: "text-emerald-400",
  running: "text-yellow-400",
  pending: "text-zinc-400",
  failed: "text-red-400",
};

/** Fallback for a status the backend introduces before the map is updated. */
export const DEFAULT_STATUS_COLOR = "text-zinc-400";

export function statusColor(status: string): string {
  return STATUS_COLORS[status] ?? DEFAULT_STATUS_COLOR;
}
