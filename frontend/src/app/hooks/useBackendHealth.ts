import { useCallback, useEffect, useRef, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const POLL_INTERVAL = 30_000; // 30s
const TIMEOUT_MS = 5_000;

export interface BackendHealth {
  connected: boolean;
  geminiConfigured: boolean;
  checking: boolean;
}

export function useBackendHealth(): BackendHealth {
  const [connected, setConnected] = useState(false);
  const [geminiConfigured, setGeminiConfigured] = useState(false);
  const [checking, setChecking] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const check = useCallback(async () => {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);

      const res = await fetch(`${API_URL}/health`, {
        signal: controller.signal,
      });
      clearTimeout(timeout);

      if (res.ok) {
        const data = await res.json();
        setConnected(true);
        setGeminiConfigured(data.gemini_configured ?? false);
      } else {
        setConnected(false);
        setGeminiConfigured(false);
      }
    } catch {
      setConnected(false);
      setGeminiConfigured(false);
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
