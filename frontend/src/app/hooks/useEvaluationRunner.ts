import { useCallback, useEffect, useRef, useState } from "react";
import { fetchEvaluations, runEvaluation } from "../api";
import type { EvaluateRequest, Evaluation } from "../types";

const POLL_INTERVAL_MS = 5_000;
const RUN_TIMEOUT_MS = 15 * 60_000;
/** Render's free tier cold-starts and blips; tolerate a few misses before giving up. */
const MAX_CONSECUTIVE_FAILURES = 5;

/** Statuses that mean the backend is still working. */
const IN_FLIGHT = new Set(["running", "pending"]);

export interface UseEvaluationRunnerOptions {
  /** Called with fresh rows on every successful poll, so the list stays live. */
  onEvaluationsUpdated: (evaluations: Evaluation[]) => void;
  /** Called once the run finishes successfully, with its evaluation id. */
  onCompleted: (evaluationId: string) => void;
}

export interface UseEvaluationRunner {
  running: boolean;
  error: string | null;
  run: (request: EvaluateRequest) => Promise<void>;
}

/**
 * Launches an evaluation and polls until it finishes.
 *
 * The backend accepts the request and returns immediately (ADR-017), so
 * completion is discovered by polling the list rather than held open on one
 * HTTP request. Every await is followed by a cancellation check: the loop can
 * outlive the page by up to fifteen minutes, and calling setState on a
 * torn-down component is the failure this guards against.
 */
export function useEvaluationRunner({
  onEvaluationsUpdated,
  onCompleted,
}: UseEvaluationRunnerOptions): UseEvaluationRunner {
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cancelledRef = useRef(false);
  useEffect(() => {
    return () => {
      cancelledRef.current = true;
    };
  }, []);

  // Held in a ref so `run` stays stable even when the caller passes inline
  // callbacks that change identity on every render.
  const callbacksRef = useRef({ onEvaluationsUpdated, onCompleted });
  useEffect(() => {
    callbacksRef.current = { onEvaluationsUpdated, onCompleted };
  }, [onEvaluationsUpdated, onCompleted]);

  const run = useCallback(async (request: EvaluateRequest) => {
    try {
      setRunning(true);
      setError(null);

      const { evaluation_id } = await runEvaluation(request);
      if (cancelledRef.current) return;

      const deadline = Date.now() + RUN_TIMEOUT_MS;
      let consecutiveFailures = 0;

      while (Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
        if (cancelledRef.current) return;

        let evaluations: Evaluation[];
        try {
          evaluations = await fetchEvaluations();
          consecutiveFailures = 0;
        } catch {
          consecutiveFailures += 1;
          if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
            if (!cancelledRef.current) {
              setError(
                "Lost connection to the backend while polling; the run may still finish — check back later.",
              );
            }
            return;
          }
          continue;
        }

        if (cancelledRef.current) return;
        callbacksRef.current.onEvaluationsUpdated(evaluations);

        const mine = evaluations.find((e) => e.id === evaluation_id);
        if (mine && !IN_FLIGHT.has(mine.status)) {
          if (mine.status === "completed") {
            callbacksRef.current.onCompleted(evaluation_id);
          } else {
            setError("Evaluation failed — check the backend logs.");
          }
          return;
        }
      }

      if (!cancelledRef.current) {
        setError("Evaluation is taking longer than expected; check back later.");
      }
    } catch (e) {
      if (!cancelledRef.current) {
        setError(e instanceof Error ? e.message : "Failed to run evaluation");
      }
    } finally {
      if (!cancelledRef.current) setRunning(false);
    }
  }, []);

  return { running, error, run };
}
