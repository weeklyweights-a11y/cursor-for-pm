import { apiClient } from "./client";
import type { Brief, BriefStatus } from "../types/briefs";

export async function generateBrief(themeId: string): Promise<{ brief_id: string; status: string }> {
  const { data } = await apiClient.post<{ data: { brief_id: string; status: string } }>(
    "/api/v1/briefs/generate",
    { theme_id: themeId }
  );
  return data.data;
}

export async function getBrief(id: string): Promise<Brief> {
  const { data } = await apiClient.get<{ data: Brief }>(`/api/v1/briefs/${id}`);
  return data.data;
}

export async function getBriefStatus(id: string): Promise<BriefStatus> {
  const { data } = await apiClient.get<{ data: BriefStatus }>(`/api/v1/briefs/${id}/status`);
  return data.data;
}

export async function getBriefsForTheme(themeId: string): Promise<Brief[]> {
  const { data } = await apiClient.get<{ data: Brief[] }>(`/api/v1/briefs/theme/${themeId}`);
  return data.data;
}

export async function getCurrentBrief(themeId: string): Promise<Brief | null> {
  try {
    const { data } = await apiClient.get<{ data: Brief }>(`/api/v1/briefs/theme/${themeId}/current`);
    return data.data;
  } catch {
    return null;
  }
}

export async function editSection(
  briefId: string,
  sectionKey: string,
  content: string
): Promise<Brief> {
  const { data } = await apiClient.patch<{ data: Brief }>(
    `/api/v1/briefs/${briefId}/sections/${sectionKey}`,
    { content }
  );
  return data.data;
}

export async function regenerateSection(
  briefId: string,
  sectionKey: string
): Promise<Brief> {
  const { data } = await apiClient.post<{ data: Brief }>(
    `/api/v1/briefs/${briefId}/sections/${sectionKey}/regenerate`
  );
  return data.data;
}

export async function evaluateSolution(
  briefId: string,
  solutionDescription: string
): Promise<Brief> {
  const { data } = await apiClient.post<{ data: Brief }>(
    `/api/v1/briefs/${briefId}/evaluate-solution`,
    { solution_description: solutionDescription }
  );
  return data.data;
}

export async function exportBriefMarkdown(
  briefId: string
): Promise<{ markdown_content: string; filename: string }> {
  const { data } = await apiClient.get<{
    data: { markdown_content: string; filename: string };
  }>(`/api/v1/briefs/${briefId}/export/markdown`);
  return data.data;
}
