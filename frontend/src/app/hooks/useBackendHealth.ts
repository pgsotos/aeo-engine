import { useCallback, useEffect, useRef, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const POLL_INTERVAL = 30_000; // 30s
const TIMEOUT_MS = 15_000; // generous: Render free tier cold-starts take >5s
const FAILURE_THRESHOLD = 2; // consecutive failures before showing "not available"

export interface BackendHealth {
  connected: boolean;
  geminiConfigured: boolean;
  checking: boolean;
}

export function useBackendHealth(): BackendHealth {
  // Optimistic: assume connected until FAILURE_THRESHOLD checks fail in a row.
  // The health path lives under /api/ because content blockers drop requests
  // to a bare /health path.
  const [connected, setConnected] = useState(true);
  const [geminiConfigured, setGeminiConfigured] = useState(false);
  const [checking, setChecking] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const failuresRef = useRef(0);

  const check = useCallback(async () => {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);

      const res = await fetch(`${API_URL}/api/health`, {
        signal: controller.signal,
      });
      clearTimeout(timeout);

      if (!res.ok) throw new Error(`status ${res.status}`);

      const data = await res.json();
      failuresRef.current = 0;
      setConnected(true);
      setGeminiConfigured(data.gemini_configured ?? false);
    } catch {
      failuresRef.current += 1;
      if (failuresRef.current >= FAILURE_THRESHOLD) {
        setConnected(false);
        setGeminiConfigured(false);
      }
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    void check();
    intervalRef.current = setInterval(() => {
      void check();
    }, POLL_INTERVAL);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [check]);

  return { connected, geminiConfigured, checking };
}
