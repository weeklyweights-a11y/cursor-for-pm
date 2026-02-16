import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { generateSpec } from "../api/specs";

const SCOPES = [
  { value: "mvp", label: "MVP", description: "Only must-have user stories, minimal technical guidance" },
  { value: "full", label: "Full", description: "All user stories with priority labels, detailed technical guidance" },
];

const AUDIENCES = [
  { value: "ai_agent", label: "AI Agent", description: "Structured for Cursor/Claude Code" },
  { value: "engineer", label: "Engineer", description: "Readable for human developers" },
  { value: "mixed", label: "Mixed", description: "Balanced for both" },
];

export function SpecConfigModal({
  briefId,
  onClose,
}: {
  briefId: string;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const [scope, setScope] = useState("full");
  const [targetAudience, setTargetAudience] = useState("mixed");
  const [customInstructions, setCustomInstructions] = useState("");
  const [expandedInstructions, setExpandedInstructions] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setError(null);
    setLoading(true);
    try {
      const { spec_id } = await generateSpec(
        briefId,
        scope,
        targetAudience,
        customInstructions.trim() || undefined
      );
      onClose();
      navigate(`/specs/${spec_id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to start spec generation.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">Generate Implementation Spec</h2>

          <p className="text-sm text-gray-600 mb-4">Scope</p>
          <div className="grid grid-cols-2 gap-3 mb-6">
            {SCOPES.map((s) => (
              <button
                key={s.value}
                type="button"
                onClick={() => setScope(s.value)}
                className={`border rounded-lg p-3 text-left ${
                  scope === s.value
                    ? "border-blue-600 bg-blue-50 ring-1 ring-blue-600"
                    : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <span className="font-medium text-gray-800">{s.label}</span>
                <p className="text-xs text-gray-500 mt-1">{s.description}</p>
              </button>
            ))}
          </div>

          <p className="text-sm text-gray-600 mb-4">Target audience</p>
          <div className="grid grid-cols-3 gap-2 mb-6">
            {AUDIENCES.map((a) => (
              <button
                key={a.value}
                type="button"
                onClick={() => setTargetAudience(a.value)}
                className={`border rounded-lg p-3 text-left ${
                  targetAudience === a.value
                    ? "border-blue-600 bg-blue-50 ring-1 ring-blue-600"
                    : "border-gray-200 hover:border-gray-300"
                }`}
              >
                <span className="font-medium text-gray-800 block">{a.label}</span>
                <span className="text-xs text-gray-500">{a.description}</span>
              </button>
            ))}
          </div>

          <div className="mb-6">
            <button
              type="button"
              onClick={() => setExpandedInstructions(!expandedInstructions)}
              className="text-sm text-gray-600 hover:underline"
            >
              {expandedInstructions ? "Hide" : "Add"} custom instructions (optional)
            </button>
            {expandedInstructions && (
              <textarea
                className="mt-2 w-full border border-gray-300 rounded p-2 text-sm min-h-[80px]"
                placeholder="e.g. We use PostgreSQL and FastAPI. Our frontend is React with Tailwind."
                value={customInstructions}
                onChange={(e) => setCustomInstructions(e.target.value)}
              />
            )}
          </div>

          {error && (
            <p className="text-sm text-red-600 mb-4">{error}</p>
          )}

          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="rounded border border-gray-300 px-4 py-2 text-sm text-gray-700"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={loading}
              className="rounded bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              {loading ? "Starting…" : "Generate"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
