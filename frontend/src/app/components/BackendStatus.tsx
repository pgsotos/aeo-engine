"use client";

import type { BackendHealth } from "../hooks/useBackendHealth";

interface BackendStatusProps {
  health: BackendHealth;
}

export default function BackendStatus({ health }: BackendStatusProps) {
  if (health.checking) {
    return (
      <div className="mb-6 flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-800/50 px-4 py-3 text-sm text-zinc-400">
        <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        Connecting to backend…
      </div>
    );
  }

  if (!health.connected) {
    return (
      <div className="mb-6 rounded-lg border border-red-800/50 bg-red-900/20 px-4 py-3 text-sm text-red-300">
        Backend not available at{" "}
        <span className="font-mono">{process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}</span>
        . Make sure the backend is running.
      </div>
    );
  }

  const missing = [
    !health.geminiConfigured && "GEMINI_API_KEY",
    !health.supabaseConfigured && "SUPABASE_URL / SUPABASE_KEY",
  ].filter(Boolean) as string[];

  if (missing.length > 0) {
    return (
      <div className="mb-6 rounded-lg border border-yellow-800/50 bg-yellow-900/20 px-4 py-3 text-sm text-yellow-300">
        Backend is up, but {missing.join(" and ")}{" "}
        {missing.length > 1 ? "are" : "is"} not configured. Add{" "}
        {missing.length > 1 ? "them" : "it"} to{" "}
        <span className="font-mono">backend/.env</span> and restart — see the
        README for where to get {missing.length > 1 ? "them" : "it"}.
      </div>
    );
  }

  return null;
}
