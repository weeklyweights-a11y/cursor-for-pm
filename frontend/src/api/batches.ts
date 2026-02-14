import type { Batch, PaginationMeta } from "../types/feedback";
import { apiClient } from "./client";

export interface BatchListResponse {
  data: Batch[];
  pagination: PaginationMeta;
}

export async function getBatches(params?: { page?: number; page_size?: number }): Promise<BatchListResponse> {
  const search = new URLSearchParams();
  if (params?.page != null) search.set("page", String(params.page));
  if (params?.page_size != null) search.set("page_size", String(params.page_size));
  const q = search.toString();
  const { data } = await apiClient.get<BatchListResponse>(`/api/v1/batches${q ? `?${q}` : ""}`);
  return data;
}

export async function getBatch(id: string): Promise<Batch> {
  const { data } = await apiClient.get<{ data: Batch }>(`/api/v1/batches/${id}`);
  return data.data;
}
