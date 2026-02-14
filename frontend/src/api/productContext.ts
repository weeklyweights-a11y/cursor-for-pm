import type {
  ProductContext,
  ProductContextCreatePayload,
  ProductContextUpdatePayload,
} from "../types/feedback";
import { apiClient } from "./client";

export async function getProductContext(): Promise<ProductContext | null> {
  try {
    const { data } = await apiClient.get<{ data: ProductContext }>("/api/v1/product-context");
    return data.data;
  } catch (err: unknown) {
    if (typeof err === "object" && err !== null && "response" in err) {
      const ax = err as { response?: { status?: number } };
      if (ax.response?.status === 404) return null;
    }
    throw err;
  }
}

export async function createProductContext(
  payload: ProductContextCreatePayload
): Promise<ProductContext> {
  const { data } = await apiClient.post<{ data: ProductContext }>(
    "/api/v1/product-context",
    payload
  );
  return data.data;
}

export async function updateProductContext(
  payload: ProductContextUpdatePayload
): Promise<ProductContext> {
  const { data } = await apiClient.patch<{ data: ProductContext }>(
    "/api/v1/product-context",
    payload
  );
  return data.data;
}
