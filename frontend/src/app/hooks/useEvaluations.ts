import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchEvaluations } from "../api";
import type { Evaluation } from "../types";

export interface UseEvaluations {
  evaluations: Evaluation[];
  loading: boolean;
  error: string | null;
  /** Replace the list wholesale — used by the run poller, which already has fresh rows. */
  replaceAll: (evaluations: Evaluation[]) => void;
  /** The freshest finished run, offered as an entry point on first visit. */
  latestCompleted: Evaluation | null;
}

/** Loads the evaluation list once on mount. */
export function useEvaluations(): UseEvaluations {
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await fetchEvaluations();
        if (cancelled) return;
        setEvaluations(data);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load evaluations");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const replaceAll = useCallback((next: Evaluation[]) => {
    setEvaluations(next);
  }, []);

  // The API returns most-recent-first, so the first completed row is the newest.
  const latestCompleted = useMemo(
    () => evaluations.find((ev) => ev.status === "completed") ?? null,
    [evaluations],
  );

  return { evaluations, loading, error, replaceAll, latestCompleted };
}
