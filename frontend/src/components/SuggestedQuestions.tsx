interface SuggestedQuestionsProps {
  onSelect: (question: string) => void;
}

const SUGGESTIONS = [
  "What are my top priorities this week?",
  "What are enterprise customers most frustrated about?",
  "Compare feedback from enterprise vs SMB",
  "What themes have the highest urgency?",
  "Show me recent critical feedback",
];

export function SuggestedQuestions({ onSelect }: SuggestedQuestionsProps) {
  return (
    <div className="space-y-2 p-2">
      <p className="text-xs font-medium text-gray-500">Suggested questions</p>
      <div className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onSelect(q)}
            className="rounded-full border border-gray-200 bg-gray-100 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-200"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
