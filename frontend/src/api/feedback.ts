import type { EnrichmentStats, ExtractionStats, FeedbackItem, PaginationMeta } from "../types/feedback";
import { apiClient } from "./client";

export interface ManualFeedbackPayload {
  content: string;
  author_name?: string;
  author_email?: string;
  organization_name?: string;
  source_description?: string;
}

export interface FeedbackListResponse {
  data: FeedbackItem[];
  pagination: PaginationMeta;
}

export async function createManualFeedback(payload: ManualFeedbackPayload): Promise<FeedbackItem> {
  const { data } = await apiClient.post<{ data: FeedbackItem }>("/api/v1/feedback/manual", payload);
  return data.data;
}

export async function uploadFeedbackCsv(file: File): Promise<{
  batch: { id: string; status: string; total_rows: number; processed_rows: number; successful_rows: number; failed_rows: number; filename: string };
  sync: boolean;
  message?: string;
}> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await apiClient.post<{ data: { batch: unknown; sync: boolean; message?: string } }>(
    "/api/v1/feedback/upload-csv",
    form
  );
  return data.data as {
    batch: { id: string; status: string; total_rows: number; processed_rows: number; successful_rows: number; failed_rows: number; filename: string };
    sync: boolean;
    message?: string;
  };
}

export async function getFeedbackItems(params: {
  page?: number;
  page_size?: number;
  source_type?: string;
  match_status?: string;
  segment?: string;
  theme_id?: string;
  outliers_only?: boolean;
  unclustered_only?: boolean;
}): Promise<FeedbackListResponse> {
  const search = new URLSearchParams();
  if (params.page != null) search.set("page", String(params.page));
  if (params.page_size != null) search.set("page_size", String(params.page_size));
  if (params.source_type) search.set("source_type", params.source_type);
  if (params.match_status) search.set("match_status", params.match_status);
  if (params.segment) search.set("segment", params.segment);
  if (params.theme_id) search.set("theme_id", params.theme_id);
  if (params.outliers_only) search.set("outliers_only", "true");
  if (params.unclustered_only) search.set("unclustered_only", "true");
  const { data } = await apiClient.get<FeedbackListResponse>(`/api/v1/feedback?${search}`);
  return data;
}

export async function getFeedbackItem(id: string): Promise<FeedbackItem> {
  const { data } = await apiClient.get<{ data: FeedbackItem }>(`/api/v1/feedback/${id}`);
  return data.data;
}

export async function deleteFeedback(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/feedback/${id}`);
}

export async function manualMatchFeedback(feedbackId: string, customerId: string): Promise<FeedbackItem> {
  const { data } = await apiClient.post<{ data: FeedbackItem }>(
    `/api/v1/feedback/${feedbackId}/manual-match`,
    { customer_id: customerId }
  );
  return data.data;
}

export async function getExtractionStats(): Promise<ExtractionStats> {
  const { data } = await apiClient.get<{ data: ExtractionStats }>(
    "/api/v1/feedback/extraction-stats"
  );
  return data.data;
}

export async function extractPending(): Promise<{ enqueued: number }> {
  const { data } = await apiClient.post<{ data: { enqueued: number } }>(
    "/api/v1/feedback/extract-pending"
  );
  return data.data;
}

export async function getEnrichmentStats(): Promise<EnrichmentStats> {
  const { data } = await apiClient.get<{ data: EnrichmentStats }>(
    "/api/v1/feedback/enrichment-stats"
  );
  return data.data;
}
