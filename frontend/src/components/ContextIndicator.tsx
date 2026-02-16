import { useState } from "react";

interface ContextIndicatorProps {
  contextUsed?: Record<string, unknown> | null;
}

export function ContextIndicator({ contextUsed }: ContextIndicatorProps) {
  const [expanded, setExpanded] = useState(false);
  if (!contextUsed) return null;
  const feedbackCount = (contextUsed.feedback_items_searched as number) ?? 0;
  const toolsCalled = (contextUsed.tools_called as string[]) ?? [];
  const themeRefs = (contextUsed.themes_referenced as string[]) ?? [];
  const summary = `Based on ${feedbackCount} feedback items${themeRefs.length ? `, ${themeRefs.length} themes` : ""}${toolsCalled.length ? `; tools: ${toolsCalled.join(", ")}` : ""}`;
  return (
    <div className="mt-1 border-t border-gray-100 pt-1 text-xs text-gray-500">
      <button type="button" onClick={() => setExpanded(!expanded)} className="hover:underline">
        {summary}
      </button>
      {expanded && (
        <pre className="mt-1 max-h-24 overflow-auto rounded bg-gray-50 p-2 text-xs">
          {JSON.stringify(contextUsed, null, 2)}
        </pre>
      )}
    </div>
  );
}
