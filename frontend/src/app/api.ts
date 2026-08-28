import type {
  Competitor,
  DashboardData,
  EvaluateRequest,
  Evaluation,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Build the error a resolve helper throws when the backend responds non-2xx.
 *
 * The backend reports actionable messages in a JSON `detail` field (e.g. 404
 * "Could not resolve competitors for 'X'"). Surface that over the raw status
 * when present, so the inline step error can show why a resolve failed instead
 * of a bare "Failed to resolve categories: 404".
 */
async function resolveErrorKind(res: Response, kind: string): Promise<Error> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail) {
      return new Error(body.detail);
    }
  } catch {
    // Non-JSON error body — fall through to the raw-status message.
  }
  return new Error(`Failed to resolve ${kind}: ${res.status}`);
}

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

export async function fetchCategories(
  brand: string,
): Promise<{ brand: string; categories: string[] }> {
  const res = await fetch(
    `${API_URL}/api/resolve-category?brand=${encodeURIComponent(brand)}`,
  );
  if (!res.ok) throw await resolveErrorKind(res, "categories");
  return res.json();
}

export async function fetchCompetitors(
  brand: string,
  category: string,
): Promise<{ brand: string; category: string; competitors: Competitor[] }> {
  const res = await fetch(
    `${API_URL}/api/resolve-competitors?brand=${encodeURIComponent(brand)}&category=${encodeURIComponent(category)}`,
  );
  if (!res.ok) throw await resolveErrorKind(res, "competitors");
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
