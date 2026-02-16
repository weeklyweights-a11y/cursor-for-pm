import { useCallback, useEffect, useRef, useState } from "react";
import {
  clearConversation,
  deleteConversation,
  getConversationMessages,
  getConversations,
  sendMessage,
} from "../api/chat";
import type { Conversation, Message, PageContext } from "../types/chat";
import { ChatInput } from "./ChatInput";
import { ChatMessage } from "./ChatMessage";
import { ContextIndicator } from "./ContextIndicator";
import { SuggestedQuestions } from "./SuggestedQuestions";

interface ChatSidebarProps {
  isOpen: boolean;
  onClose: () => void;
  pageContext?: PageContext | null;
}

export function ChatSidebar({ isOpen, onClose, pageContext }: ChatSidebarProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadConversations = useCallback(() => {
    getConversations(1, 50)
      .then((res) => setConversations(res.data))
      .catch(() => setConversations([]));
  }, []);

  const loadMessages = useCallback((conversationId: string) => {
    getConversationMessages(conversationId, 1, 100)
      .then((res) => setMessages(res.data))
      .catch(() => setMessages([]));
  }, []);

  useEffect(() => {
    if (isOpen) loadConversations();
  }, [isOpen, loadConversations]);

  useEffect(() => {
    if (currentConversationId) loadMessages(currentConversationId);
    else setMessages([]);
  }, [currentConversationId, loadMessages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = useCallback(
    (text: string) => {
      setLoading(true);
      sendMessage(text, currentConversationId, pageContext ?? undefined)
        .then((res) => {
          const userMsg: Message = {
            id: `temp-${Date.now()}`,
            conversation_id: res.conversation_id,
            role: "user",
            content: text,
            created_at: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, userMsg, res.message]);
          if (!currentConversationId) {
            setCurrentConversationId(res.conversation_id);
            loadConversations();
          }
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    },
    [currentConversationId, pageContext, loadConversations]
  );

  const handleNewConversation = useCallback(() => {
    setCurrentConversationId(null);
    setMessages([]);
  }, []);

  const handleSelectConversation = useCallback((id: string) => {
    setCurrentConversationId(id);
  }, []);

  const handleDeleteConversation = useCallback(
    (id: string) => {
      deleteConversation(id).then(() => {
        loadConversations();
        if (currentConversationId === id) {
          setCurrentConversationId(null);
          setMessages([]);
        }
      });
    },
    [currentConversationId, loadConversations]
  );

  if (!isOpen) return null;

  return (
    <aside className="flex w-full max-w-[40vw] flex-col border-l border-gray-200 bg-white shadow-lg">
      <div className="flex items-center justify-between border-b border-gray-200 p-3">
        <h2 className="font-semibold text-gray-800">Ask your data</h2>
        <div className="flex items-center gap-2">
          <select
            className="rounded border border-gray-300 px-2 py-1 text-sm"
            value={currentConversationId ?? ""}
            onChange={(e) => handleSelectConversation(e.target.value)}
          >
            <option value="">New conversation</option>
            {conversations.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title || "Untitled"} ({c.message_count})
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={handleNewConversation}
            className="rounded bg-gray-100 px-2 py-1 text-sm hover:bg-gray-200"
          >
            New
          </button>
          <button type="button" onClick={onClose} className="rounded p-1 hover:bg-gray-100" aria-label="Close">
            ×
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-3">
        {messages.length === 0 && !loading && <SuggestedQuestions onSelect={handleSend} />}
        {messages.map((m) => (
          <div key={m.id}>
            <ChatMessage message={m} />
            {m.role === "assistant" && <ContextIndicator contextUsed={m.context_used} />}
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="flex gap-1 rounded-lg bg-gray-100 px-4 py-2">
              <span className="animate-bounce">.</span>
              <span className="animate-bounce animation-delay-100">.</span>
              <span className="animate-bounce animation-delay-200">.</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <ChatInput onSend={handleSend} disabled={loading} />
    </aside>
  );
}
