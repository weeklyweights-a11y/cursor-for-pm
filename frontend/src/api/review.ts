import type { PaginationMeta } from "../types/feedback";
import type { ReviewQueueItem } from "../types/review";
import { apiClient } from "./client";

export interface ReviewQueueListResponse {
  data: ReviewQueueItem[];
  pagination: PaginationMeta;
}

export async function getPendingReviews(params: {
  page?: number;
  page_size?: number;
}): Promise<ReviewQueueListResponse> {
  const search = new URLSearchParams();
  if (params.page != null) search.set("page", String(params.page));
  if (params.page_size != null) search.set("page_size", String(params.page_size));
  const { data } = await apiClient.get<ReviewQueueListResponse>(
    `/api/v1/review-queue?${search}`
  );
  return data;
}

export async function getReviewCount(): Promise<number> {
  const { data } = await apiClient.get<{ data: { count: number } }>(
    "/api/v1/review-queue/count"
  );
  return data.data.count;
}

export async function confirmReview(reviewId: string): Promise<ReviewQueueItem> {
  const { data } = await apiClient.post<{ data: ReviewQueueItem }>(
    `/api/v1/review-queue/${reviewId}/confirm`
  );
  return data.data;
}

export async function rejectReview(reviewId: string): Promise<ReviewQueueItem> {
  const { data } = await apiClient.post<{ data: ReviewQueueItem }>(
    `/api/v1/review-queue/${reviewId}/reject`
  );
  return data.data;
}

export async function skipReview(reviewId: string): Promise<ReviewQueueItem> {
  const { data } = await apiClient.post<{ data: ReviewQueueItem }>(
    `/api/v1/review-queue/${reviewId}/skip`
  );
  return data.data;
}

export async function manualMatchReview(
  reviewId: string,
  customerId: string
): Promise<ReviewQueueItem> {
  const { data } = await apiClient.post<{ data: ReviewQueueItem }>(
    `/api/v1/review-queue/${reviewId}/manual-match`,
    { customer_id: customerId }
  );
  return data.data;
}
