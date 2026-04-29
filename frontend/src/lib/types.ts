export type StateName =
  | "plan"
  | "search"
  | "reason"
  | "verify"
  | "answer"
  | "done"
  | "error";

export interface Citation {
  id: string;
  rank: number;
  title: string;
  url: string;
  source: string;
  relevance_score: number;
  snippet: string;
}

export interface Metrics {
  faithfulness: number | null;
  citation_accuracy: number | null;
  latency_seconds: number;
  cost_usd: number;
  tokens_in: number;
  tokens_out: number;
  citation_count: number | null;
  num_search_hops: number | null;
}

export interface AgentStateUpdate {
  session_id: string;
  state: StateName;
  step_index: number;
  content: string;
  metadata: Record<string, unknown>;
  is_final: boolean;
  timestamp: string;
}

export interface ResearchRequest {
  query: string;
  language?: string;
  max_steps?: number;
}

export interface BenchResult {
  id: string;
  language: string;
  faithfulness: number;
  citation_accuracy: number;
  latency_seconds: number;
  cost_usd: number;
  tokens_in: number;
  tokens_out: number;
  citation_count: number;
  num_search_hops: number;
}
