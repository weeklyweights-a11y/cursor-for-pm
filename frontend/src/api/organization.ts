import type { Organization } from "../types/auth";
import { apiClient } from "./client";

export async function getOrganization(): Promise<Organization> {
  const { data } = await apiClient.get<{ data: Organization }>("/api/v1/organization");
  return data.data;
}

export async function updateOrganization(name: string): Promise<Organization> {
  const { data } = await apiClient.patch<{ data: Organization }>("/api/v1/organization", {
    name,
  });
  return data.data;
}
