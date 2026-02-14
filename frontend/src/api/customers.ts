import type { Customer, CustomerDetail, CustomerUploadResult, TopCustomer } from "../types/customers";
import type { PaginationMeta } from "../types/feedback";
import { apiClient } from "./client";

export interface CustomerListResponse {
  data: Customer[];
  pagination: PaginationMeta;
}

export async function uploadCustomersCsv(file: File): Promise<CustomerUploadResult> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await apiClient.post<{ data: CustomerUploadResult }>(
    "/api/v1/customers/upload",
    form
  );
  return data.data;
}

export async function getCustomers(params: {
  page?: number;
  page_size?: number;
  segment?: string;
  search?: string;
}): Promise<CustomerListResponse> {
  const search = new URLSearchParams();
  if (params.page != null) search.set("page", String(params.page));
  if (params.page_size != null) search.set("page_size", String(params.page_size));
  if (params.segment) search.set("segment", params.segment);
  if (params.search) search.set("search", params.search);
  const { data } = await apiClient.get<CustomerListResponse>(`/api/v1/customers?${search}`);
  return data;
}

export async function getTopCustomers(limit?: number): Promise<TopCustomer[]> {
  const params = limit != null ? `?limit=${limit}` : "";
  const { data } = await apiClient.get<{ data: TopCustomer[] }>(`/api/v1/customers/top${params}`);
  return data.data;
}

export async function getCustomer(id: string): Promise<CustomerDetail> {
  const { data } = await apiClient.get<{ data: CustomerDetail }>(`/api/v1/customers/${id}`);
  return data.data;
}

export async function deactivateCustomer(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/customers/${id}`);
}
