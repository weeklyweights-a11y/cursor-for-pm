import { apiClient } from "./client";
import type { Spec, SpecStatus, SpecExportResponse } from "../types/specs";

export async function generateSpec(
  briefId: string,
  scope: string,
  targetAudience: string,
  customInstructions?: string | null
): Promise<{ spec_id: string; status: string }> {
  const { data } = await apiClient.post<{ data: { spec_id: string; status: string } }>(
    "/api/v1/specs/generate",
    {
      brief_id: briefId,
      scope,
      target_audience: targetAudience,
      custom_instructions: customInstructions ?? undefined,
    }
  );
  return data.data;
}

export async function getSpec(id: string): Promise<Spec> {
  const { data } = await apiClient.get<{ data: Spec }>(`/api/v1/specs/${id}`);
  return data.data;
}

export async function getSpecStatus(id: string): Promise<SpecStatus> {
  const { data } = await apiClient.get<{ data: SpecStatus }>(`/api/v1/specs/${id}/status`);
  return data.data;
}

export async function getSpecsForBrief(briefId: string): Promise<Spec[]> {
  const { data } = await apiClient.get<{ data: Spec[] }>(
    `/api/v1/specs/brief/${briefId}`
  );
  return data.data;
}

export async function getCurrentSpecForBrief(briefId: string): Promise<Spec | null> {
  try {
    const { data } = await apiClient.get<{ data: Spec }>(
      `/api/v1/specs/brief/${briefId}/current`
    );
    return data.data;
  } catch {
    return null;
  }
}

export async function getSpecsForTheme(themeId: string): Promise<Spec[]> {
  const { data } = await apiClient.get<{ data: Spec[] }>(
    `/api/v1/specs/theme/${themeId}`
  );
  return data.data;
}

export async function editSpecSection(
  specId: string,
  sectionKey: string,
  content: string
): Promise<Spec> {
  const { data } = await apiClient.patch<{ data: Spec }>(
    `/api/v1/specs/${specId}/sections/${sectionKey}`,
    { content }
  );
  return data.data;
}

export async function regenerateSpecSection(
  specId: string,
  sectionKey: string
): Promise<Spec> {
  const { data } = await apiClient.post<{ data: Spec }>(
    `/api/v1/specs/${specId}/sections/${sectionKey}/regenerate`
  );
  return data.data;
}

export async function exportSpecMarkdown(
  specId: string
): Promise<SpecExportResponse> {
  const { data } = await apiClient.get<{ data: SpecExportResponse }>(
    `/api/v1/specs/${specId}/export/markdown`
  );
  return data.data;
}

export async function exportSpecCursor(
  specId: string
): Promise<SpecExportResponse> {
  const { data } = await apiClient.get<{ data: SpecExportResponse }>(
    `/api/v1/specs/${specId}/export/cursor`
  );
  return data.data;
}
