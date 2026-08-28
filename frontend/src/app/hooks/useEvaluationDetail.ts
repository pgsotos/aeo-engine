import { useCallback, useState } from "react";
import { fetchEvaluationDetail } from "../api";
import type { DashboardData } from "../types";

export interface UseEvaluationDetail {
  dashboard: DashboardData | null;
  selectedId: string | null;
  loading: boolean;
  error: string | null;
  /** Open an evaluation: marks it selected, then loads its full detail. */
  select: (id: string) => void;
  /** Return to the list view. */
  clear: () => void;
}

/**
 * Owns the currently open evaluation.
 *
 * `selectedId` is set before the fetch resolves so the list can highlight the
 * row immediately; `dashboard` stays null until the payload lands, which is
 * what switches the page from the list view to the dashboard view.
 */
export function useEvaluationDetail(): UseEvaluationDetail {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const select = useCallback((id: string) => {
    setSelectedId(id);

    void (async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchEvaluationDetail(id);
        setDashboard(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load detail");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const clear = useCallback(() => {
    setDashboard(null);
    setSelectedId(null);
    setError(null);
  }, []);

  return { dashboard, selectedId, loading, error, select, clear };
}
