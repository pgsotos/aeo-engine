import type { DashboardData, EvaluateRequest, Evaluation } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchEvaluations(): Promise<Evaluation[]> {
  const res = await fetch(`${API_URL}/api/evaluations`);
  if (!res.ok) throw new Error(`Failed to fetch evaluations: ${res.status}`);
  return res.json();
}

export async function fetchEvaluationDetail(
  evaluationId: string,
): Promise<DashboardData> {
  const res = await fetch(`${API_URL}/api/evaluations/${evaluationId}`);
  if (!res.ok) throw new Error(`Failed to fetch evaluation: ${res.status}`);
  return res.json();
}

export async function runEvaluation(
  request: EvaluateRequest,
): Promise<{ evaluation_id: string; status: string }> {
  const res = await fetch(`${API_URL}/api/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) throw new Error(`Failed to run evaluation: ${res.status}`);
  return res.json();
}
