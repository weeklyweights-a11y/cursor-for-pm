import { apiClient } from "./client";

export interface ReEnrichResponse {
  items_queued: number;
}

export async function reEnrichUnmatched(): Promise<ReEnrichResponse> {
  const { data } = await apiClient.post<{ data: ReEnrichResponse }>(
    "/api/v1/enrichment/re-enrich"
  );
  return data.data;
}
