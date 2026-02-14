import type { Theme, ThemeListResponse } from "../types/themes";
import type { FeedbackItem, PaginationMeta } from "../types/feedback";
import { apiClient } from "./client";

export async function getThemes(params: {
  page?: number;
  page_size?: number;
  sort_by?: string;
}): Promise<ThemeListResponse> {
  const search = new URLSearchParams();
  if (params.page != null) search.set("page", String(params.page));
  if (params.page_size != null) search.set("page_size", String(params.page_size));
  if (params.sort_by) search.set("sort_by", params.sort_by);
  const { data } = await apiClient.get<{ data: Theme[]; pagination: ThemeListResponse["pagination"] }>(
    `/api/v1/themes?${search}`
  );
  return { data: data.data, pagination: data.pagination };
}

export async function getTheme(id: string): Promise<Theme> {
  const { data } = await apiClient.get<{ data: Theme }>(`/api/v1/themes/${id}`);
  return data.data;
}

export async function getThemeFeedback(
  themeId: string,
  params: { page?: number; page_size?: number }
): Promise<{ data: FeedbackItem[]; pagination: PaginationMeta }> {
  const search = new URLSearchParams();
  if (params.page != null) search.set("page", String(params.page));
  if (params.page_size != null) search.set("page_size", String(params.page_size));
  const { data } = await apiClient.get<{ data: FeedbackItem[]; pagination: PaginationMeta }>(
    `/api/v1/themes/${themeId}/feedback?${search}`
  );
  return data;
}

export async function getOutliers(params: {
  page?: number;
  page_size?: number;
}): Promise<{ data: FeedbackItem[]; pagination: PaginationMeta }> {
  const search = new URLSearchParams();
  if (params.page != null) search.set("page", String(params.page));
  if (params.page_size != null) search.set("page_size", String(params.page_size));
  const { data } = await apiClient.get<{ data: FeedbackItem[]; pagination: PaginationMeta }>(
    `/api/v1/themes/outliers?${search}`
  );
  return data;
}
