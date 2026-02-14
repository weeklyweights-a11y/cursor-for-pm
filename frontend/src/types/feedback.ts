export interface FeedbackItem {
  id: string;
  org_id: string;
  content: string;
  source_type: string;
  source_id: string;
  timestamp: string | null;
  author_email: string | null;
  author_name: string | null;
  organization_name: string | null;
  metadata: Record<string, unknown> | null;
  batch_id: string | null;
  created_at: string;
  updated_at: string;
  // Extraction (Phase 3)
  pain_point?: string | null;
  topic?: string | null;
  related_feature?: string | null;
  is_existing_feature?: boolean | null;
  feature_gap?: string | null;
  urgency?: string | null;
  sentiment?: string | null;
  verbatim_quote?: string | null;
  extraction_confidence?: number | null;
  extraction_status?: string | null;
  raw_llm_response?: string | null;
  extracted_at?: string | null;
  // Enrichment (Phase 4)
  customer_id?: string | null;
  customer_domain?: string | null;
  customer_name?: string | null;
  segment?: string | null;
  match_method?: string | null;
  match_confidence?: number | null;
  match_status?: string | null;
  enriched_at?: string | null;
  // Phase 5
  theme_id?: string | null;
  theme_name?: string | null;
  is_outlier?: boolean | null;
  clustered_at?: string | null;
}

export interface ExtractionStats {
  total: number;
  pending: number;
  completed: number;
  failed: number;
}

export interface EnrichmentStats {
  total: number;
  matched: number;
  pm_review: number;
  unmatched: number;
}

export interface ProductContext {
  id: string;
  org_id: string;
  product_name: string;
  product_description: string;
  existing_features: string[];
  target_users: string | null;
  known_limitations: string[] | null;
  additional_context: string | null;
}

export interface ProductContextCreatePayload {
  product_name: string;
  product_description: string;
  existing_features?: string[];
  target_users?: string | null;
  known_limitations?: string[] | null;
  additional_context?: string | null;
}

export interface ProductContextUpdatePayload {
  product_name?: string;
  product_description?: string;
  existing_features?: string[];
  target_users?: string | null;
  known_limitations?: string[] | null;
  additional_context?: string | null;
}

export interface Batch {
  id: string;
  org_id: string;
  filename: string;
  total_rows: number;
  processed_rows: number;
  successful_rows: number;
  failed_rows: number;
  status: string;
  error_message: string | null;
  column_mapping: Record<string, number> | null;
  created_at: string;
  updated_at: string;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface SlackChannel {
  id: string;
  name: string;
}

export interface SlackConnectionStatus {
  connected: boolean;
  team_name: string | null;
  channels: string[];
}
