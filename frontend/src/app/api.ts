import type { DashboardData, Evaluation } from "./types";

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
  brand = "Linear",
  samplingN?: number,
): Promise<{ evaluation_id: string; status: string }> {
  const params = new URLSearchParams({ brand });
  if (samplingN !== undefined) params.set("sampling_n", String(samplingN));

  const res = await fetch(`${API_URL}/api/evaluate?${params}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Failed to run evaluation: ${res.status}`);
  return res.json();
}
