import type { ChatResponse, Conversation, Message, PageContext, PaginationMeta } from "../types/chat";
import { apiClient } from "./client";

export async function sendMessage(
  content: string,
  conversationId?: string | null,
  pageContext?: PageContext | null
): Promise<ChatResponse> {
  const payload: { content: string; conversation_id?: string; page_context?: PageContext } = { content };
  if (conversationId) payload.conversation_id = conversationId;
  if (pageContext) payload.page_context = pageContext;
  const { data } = await apiClient.post<{ data: { message: Message; conversation_id: string } }>(
    "/api/v1/chat/send",
    payload
  );
  return data.data as ChatResponse;
}

export async function getConversations(
  page?: number,
  pageSize?: number
): Promise<{ data: Conversation[]; pagination: PaginationMeta }> {
  const params = new URLSearchParams();
  if (page != null) params.set("page", String(page));
  if (pageSize != null) params.set("page_size", String(pageSize));
  const { data } = await apiClient.get<{ data: Conversation[]; pagination: PaginationMeta }>(
    `/api/v1/chat/conversations?${params}`
  );
  return data;
}

export async function getConversationMessages(
  conversationId: string,
  page?: number,
  pageSize?: number
): Promise<{ data: Message[]; pagination: PaginationMeta }> {
  const params = new URLSearchParams();
  if (page != null) params.set("page", String(page));
  if (pageSize != null) params.set("page_size", String(pageSize));
  const { data } = await apiClient.get<{ data: Message[]; pagination: PaginationMeta }>(
    `/api/v1/chat/conversations/${conversationId}/messages?${params}`
  );
  return data;
}

export async function deleteConversation(conversationId: string): Promise<void> {
  await apiClient.delete(`/api/v1/chat/conversations/${conversationId}`);
}

export async function clearConversation(conversationId: string): Promise<void> {
  await apiClient.post(`/api/v1/chat/conversations/${conversationId}/clear`);
}
