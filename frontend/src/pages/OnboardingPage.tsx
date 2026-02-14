import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { createProductContext } from "../api/productContext";
import type { ProductContextCreatePayload } from "../types/feedback";

function parseTags(s: string): string[] {
  return s
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
}

export function OnboardingPage() {
  const navigate = useNavigate();
  const [productName, setProductName] = useState("");
  const [productDescription, setProductDescription] = useState("");
  const [existingFeaturesText, setExistingFeaturesText] = useState("");
  const [targetUsers, setTargetUsers] = useState("");
  const [knownLimitationsText, setKnownLimitationsText] = useState("");
  const [additionalContext, setAdditionalContext] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!productName.trim() || !productDescription.trim()) {
      setError("Product name and description are required.");
      return;
    }
    setSubmitting(true);
    try {
      const payload: ProductContextCreatePayload = {
        product_name: productName.trim(),
        product_description: productDescription.trim(),
        existing_features: parseTags(existingFeaturesText),
        target_users: targetUsers.trim() || null,
        known_limitations: parseTags(knownLimitationsText).length
          ? parseTags(knownLimitationsText)
          : null,
        additional_context: additionalContext.trim() || null,
      };
      await createProductContext(payload);
      navigate("/dashboard", { replace: true });
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { error?: { message?: string }; detail?: string } } };
      setError(
        ax?.response?.data?.error?.message ??
          ax?.response?.data?.detail ??
          "Failed to save. Try again."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Layout>
      <h1 className="text-2xl font-semibold text-gray-800 mb-2">Product context</h1>
      <p className="text-gray-600 mb-6">
        Tell us about your product so we can better understand feedback. You can update this later in Settings.
      </p>
      <form onSubmit={handleSubmit} className="max-w-xl space-y-4">
        {error && (
          <p className="text-sm text-red-600" role="alert">
            {error}
          </p>
        )}
        <div>
          <label htmlFor="product_name" className="block text-sm font-medium text-gray-700 mb-1">
            Product name *
          </label>
          <input
            id="product_name"
            type="text"
            value={productName}
            onChange={(e) => setProductName(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            maxLength={255}
            required
          />
        </div>
        <div>
          <label htmlFor="product_description" className="block text-sm font-medium text-gray-700 mb-1">
            Product description *
          </label>
          <textarea
            id="product_description"
            value={productDescription}
            onChange={(e) => setProductDescription(e.target.value)}
            rows={3}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            required
          />
        </div>
        <div>
          <label htmlFor="existing_features" className="block text-sm font-medium text-gray-700 mb-1">
            Existing features
          </label>
          <input
            id="existing_features"
            type="text"
            value={existingFeaturesText}
            onChange={(e) => setExistingFeaturesText(e.target.value)}
            placeholder="e.g. Search, Filters, Export"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
          <p className="mt-1 text-xs text-gray-500">Comma-separated</p>
        </div>
        <div>
          <label htmlFor="target_users" className="block text-sm font-medium text-gray-700 mb-1">
            Target users
          </label>
          <input
            id="target_users"
            type="text"
            value={targetUsers}
            onChange={(e) => setTargetUsers(e.target.value)}
            placeholder="e.g. Product managers, Support teams"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            maxLength={500}
          />
        </div>
        <div>
          <label htmlFor="known_limitations" className="block text-sm font-medium text-gray-700 mb-1">
            Known limitations
          </label>
          <input
            id="known_limitations"
            type="text"
            value={knownLimitationsText}
            onChange={(e) => setKnownLimitationsText(e.target.value)}
            placeholder="e.g. No mobile app, Limited API"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
          <p className="mt-1 text-xs text-gray-500">Comma-separated</p>
        </div>
        <div>
          <label htmlFor="additional_context" className="block text-sm font-medium text-gray-700 mb-1">
            Additional context
          </label>
          <textarea
            id="additional_context"
            value={additionalContext}
            onChange={(e) => setAdditionalContext(e.target.value)}
            rows={2}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Saving..." : "Save and continue"}
          </button>
        </div>
      </form>
    </Layout>
  );
}
