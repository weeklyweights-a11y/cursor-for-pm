import { useState } from "react";
import { createManualFeedback } from "../api/feedback";
import type { ManualFeedbackPayload } from "../api/feedback";

interface ManualFeedbackFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function ManualFeedbackForm({ onSuccess, onCancel }: ManualFeedbackFormProps) {
  const [content, setContent] = useState("");
  const [authorName, setAuthorName] = useState("");
  const [authorEmail, setAuthorEmail] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [sourceDescription, setSourceDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!content.trim()) {
      setError("Feedback text is required.");
      return;
    }
    setSubmitting(true);
    try {
      const payload: ManualFeedbackPayload = { content: content.trim() };
      if (authorName.trim()) payload.author_name = authorName.trim();
      if (authorEmail.trim()) payload.author_email = authorEmail.trim();
      if (organizationName.trim()) payload.organization_name = organizationName.trim();
      if (sourceDescription.trim()) payload.source_description = sourceDescription.trim();
      await createManualFeedback(payload);
      setContent("");
      setAuthorName("");
      setAuthorEmail("");
      setOrganizationName("");
      setSourceDescription("");
      onSuccess?.();
    } catch (err: unknown) {
      setError(err && typeof err === "object" && "response" in err
        ? (err as { response?: { data?: { error?: { message?: string } } } }).response?.data?.error?.message || "Failed to submit"
        : "Failed to submit");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 max-w-xl">
      <div>
        <label htmlFor="content" className="block text-sm font-medium text-gray-700">Feedback text *</label>
        <textarea
          id="content"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={4}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          placeholder="Paste or type the feedback..."
        />
      </div>
      <div>
        <label htmlFor="authorName" className="block text-sm font-medium text-gray-700">Author name</label>
        <input
          id="authorName"
          type="text"
          value={authorName}
          onChange={(e) => setAuthorName(e.target.value)}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-blue-500"
        />
      </div>
      <div>
        <label htmlFor="authorEmail" className="block text-sm font-medium text-gray-700">Author email</label>
        <input
          id="authorEmail"
          type="email"
          value={authorEmail}
          onChange={(e) => setAuthorEmail(e.target.value)}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-blue-500"
        />
      </div>
      <div>
        <label htmlFor="organizationName" className="block text-sm font-medium text-gray-700">Organization name</label>
        <input
          id="organizationName"
          type="text"
          value={organizationName}
          onChange={(e) => setOrganizationName(e.target.value)}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-blue-500"
        />
      </div>
      <div>
        <label htmlFor="sourceDescription" className="block text-sm font-medium text-gray-700">Source description</label>
        <input
          id="sourceDescription"
          type="text"
          value={sourceDescription}
          onChange={(e) => setSourceDescription(e.target.value)}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          placeholder="e.g. Sales call with BigCorp"
        />
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting ? "Submitting..." : "Submit feedback"}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
