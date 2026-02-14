import type { ClusteringStatus } from "../types/themes";
import { apiClient } from "./client";

export async function runClustering(): Promise<{ status: string; clustering: ClusteringStatus }> {
  const { data } = await apiClient.post<{ data: { status: string; clustering: ClusteringStatus } }>(
    "/api/v1/clustering/run"
  );
  return data.data;
}

export async function getClusteringStatus(): Promise<ClusteringStatus> {
  const { data } = await apiClient.get<{ data: ClusteringStatus }>("/api/v1/clustering/status");
  return data.data;
}

export async function backfillEmbeddings(): Promise<{ enqueued: number }> {
  const { data } = await apiClient.post<{ data: { enqueued: number } }>(
    "/api/v1/clustering/backfill-embeddings"
  );
  return data.data;
}
