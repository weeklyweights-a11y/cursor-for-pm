export interface Theme {
  id: string;
  org_id: string;
  name: string;
  description: string | null;
  mention_count: number;
  unique_customers: number;
  segment_breakdown: Record<string, number> | null;
  urgency_breakdown: Record<string, number> | null;
  sentiment_breakdown: Record<string, number> | null;
  top_quotes: string[] | null;
  priority_score: number;
  score_breakdown: Record<string, { raw?: number; normalized?: number; weighted?: number }> | null;
  is_current: boolean;
  created_at: string;
  updated_at: string;
}

export interface ThemeListResponse {
  data: Theme[];
  pagination: { page: number; page_size: number; total: number; total_pages: number };
}

export interface ScoringConfig {
  id: string;
  org_id: string;
  goals: string[] | null;
  target_segments: string[] | null;
  weight_volume: number;
  weight_reach: number;
  weight_urgency: number;
  weight_sentiment: number;
  weight_strategic_fit: number;
  created_at: string;
  updated_at: string;
}

export interface ScoringConfigUpdatePayload {
  goals?: string[] | null;
  target_segments?: string[] | null;
  weight_volume?: number;
  weight_reach?: number;
  weight_urgency?: number;
  weight_sentiment?: number;
  weight_strategic_fit?: number;
}

export interface ClusteringStatus {
  is_running: boolean;
  last_run_at: string | null;
  last_run_result: { clusters_found?: number; outliers?: number; duration_ms?: number } | null;
  items_pending: number;
}
