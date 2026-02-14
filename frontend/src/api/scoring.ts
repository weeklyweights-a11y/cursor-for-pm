import type { ScoringConfig, ScoringConfigUpdatePayload } from "../types/themes";
import { apiClient } from "./client";

export async function getScoringConfig(): Promise<ScoringConfig> {
  const { data } = await apiClient.get<{ data: ScoringConfig }>("/api/v1/scoring/config");
  return data.data;
}

export async function updateScoringConfig(payload: ScoringConfigUpdatePayload): Promise<ScoringConfig> {
  const { data } = await apiClient.patch<{ data: ScoringConfig }>("/api/v1/scoring/config", payload);
  return data.data;
}

export async function reScore(): Promise<void> {
  await apiClient.post("/api/v1/scoring/re-score");
}
