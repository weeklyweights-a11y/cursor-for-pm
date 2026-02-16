export interface Message {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  context_used?: Record<string, unknown> | null;
  tool_calls?: Record<string, unknown> | null;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string | null;
  is_active: boolean;
  message_count: number;
  last_message_at: string | null;
  created_at: string;
}

export interface ChatResponse {
  message: Message;
  conversation_id: string;
}

export interface PageContext {
  type: "theme" | "feedback" | "customer";
  id: string;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}
