export type PromptType = "direct" | "comparative" | "use_case" | "feature" | "negative";
export type Classification = "direct_winner" | "alternative_mention" | "omitted";

export interface Evaluation {
  id: string;
  brand: string;
  category: string;
  sampling_n: number;
  status: string;
  consistency: number | null;
  created_at: string;
  completed_at: string | null;
  /** Brands scored alongside the focus brand. Empty while a run is in flight. */
  competitors?: string[];
}

export interface MetricSummary {
  evaluation_id: string;
  prompt_type: PromptType;
  brand: string;
  win_rate: number;
  share_of_voice: number | null;
  ci_lower: number;
  ci_upper: number;
  total_runs: number;
  direct_wins: number;
  alternative_mentions: number;
  omitted: number;
}

export interface GeminiResponse {
  id: string;
  evaluation_id: string;
  prompt_id: string;
  run_index: number;
  model_id: string;
  raw_text: string;
  created_at: string;
}

export interface ClassificationResult {
  response_id: string;
  brand: string;
  classification: Classification;
  first_mention_position: number | null;
  mention_count: number;
  confidence_score: number;
}

export interface Competitor {
  name: string;
  reason: string;
}

export interface DashboardData {
  evaluation: Evaluation;
  metrics: MetricSummary[];
  responses: GeminiResponse[];
  classifications: ClassificationResult[];
}

export interface EvaluateRequest {
  brand: string;
  category: string;
  competitors: string[];
  sampling_n?: number;
}

export const PROMPT_TYPE_LABELS: Record<PromptType, string> = {
  direct: "Direct",
  comparative: "Comparative",
  use_case: "Use Case",
  feature: "Feature",
  negative: "Negative",
};
