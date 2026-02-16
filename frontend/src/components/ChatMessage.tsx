import ReactMarkdown from "react-markdown";
import { Link } from "react-router-dom";
import type { Message } from "../types/chat";

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div
        className={`max-w-[85%] rounded-lg px-4 py-2 ${
          isUser ? "bg-blue-600 text-white" : "bg-white border border-gray-200 text-gray-800"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm">{message.content}</p>
        ) : (
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown
              components={{
                blockquote: ({ node, ...props }) => (
                  <blockquote className="border-l-4 border-gray-300 pl-3 my-2 bg-gray-50 py-1 rounded" {...props} />
                ),
                a: ({ href, children }) =>
                  href?.startsWith("/") ? (
                    <Link to={href} className="text-blue-600 hover:underline">
                      {children}
                    </Link>
                  ) : (
                    <a href={href} className="text-blue-600 hover:underline">
                      {children}
                    </a>
                  ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
