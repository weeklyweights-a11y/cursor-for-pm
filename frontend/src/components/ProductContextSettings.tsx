import { useState, useEffect } from "react";
import { getProductContext, updateProductContext } from "../api/productContext";
import type { ProductContext } from "../types/feedback";

function parseTags(s: string): string[] {
  return s
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
}

export function ProductContextSettings({
  error,
  setError,
}: {
  error: string | null;
  setError: (s: string | null) => void;
}) {
  const [productContext, setProductContext] = useState<ProductContext | null>(null);
  const [editingContext, setEditingContext] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editFeaturesText, setEditFeaturesText] = useState("");
  const [editTargetUsers, setEditTargetUsers] = useState("");
  const [editLimitationsText, setEditLimitationsText] = useState("");
  const [editAdditional, setEditAdditional] = useState("");
  const [savingContext, setSavingContext] = useState(false);

  useEffect(() => {
    getProductContext()
      .then(setProductContext)
      .catch(() => setProductContext(null));
  }, []);

  const startEditContext = () => {
    if (productContext) {
      setEditName(productContext.product_name);
      setEditDescription(productContext.product_description);
      setEditFeaturesText((productContext.existing_features || []).join(", "));
      setEditTargetUsers(productContext.target_users || "");
      setEditLimitationsText((productContext.known_limitations || []).join(", "));
      setEditAdditional(productContext.additional_context || "");
      setEditingContext(true);
    }
  };

  const saveContext = async () => {
    setError(null);
    setSavingContext(true);
    try {
      const updated = await updateProductContext({
        product_name: editName.trim(),
        product_description: editDescription.trim(),
        existing_features: parseTags(editFeaturesText),
        target_users: editTargetUsers.trim() || null,
        known_limitations: parseTags(editLimitationsText).length ? parseTags(editLimitationsText) : null,
        additional_context: editAdditional.trim() || null,
      });
      setProductContext(updated);
      setEditingContext(false);
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { error?: { message?: string }; detail?: string } } };
      setError(ax?.response?.data?.error?.message ?? ax?.response?.data?.detail ?? "Failed to save.");
    } finally {
      setSavingContext(false);
    }
  };

  return (
    <section className="mb-8">
      <h2 className="text-lg font-medium text-gray-700 mb-2">Product context</h2>
      {error && <p className="text-sm text-red-600 mb-2">{error}</p>}
      {!productContext ? (
        <p className="text-gray-500">No product context set. Complete onboarding first.</p>
      ) : editingContext ? (
        <div className="space-y-3 max-w-xl">
          <input
            type="text"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            placeholder="Product name"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
          <textarea
            value={editDescription}
            onChange={(e) => setEditDescription(e.target.value)}
            placeholder="Description"
            rows={2}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
          <input
            type="text"
            value={editFeaturesText}
            onChange={(e) => setEditFeaturesText(e.target.value)}
            placeholder="Existing features (comma-separated)"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
          <input
            type="text"
            value={editTargetUsers}
            onChange={(e) => setEditTargetUsers(e.target.value)}
            placeholder="Target users"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
          <input
            type="text"
            value={editLimitationsText}
            onChange={(e) => setEditLimitationsText(e.target.value)}
            placeholder="Known limitations (comma-separated)"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
          <textarea
            value={editAdditional}
            onChange={(e) => setEditAdditional(e.target.value)}
            placeholder="Additional context"
            rows={2}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={saveContext}
              disabled={savingContext}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {savingContext ? "Saving..." : "Save"}
            </button>
            <button
              type="button"
              onClick={() => setEditingContext(false)}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="text-sm text-gray-700 space-y-1">
          <p><strong>{productContext.product_name}</strong></p>
          <p>{productContext.product_description}</p>
          {productContext.existing_features?.length ? (
            <p>Features: {productContext.existing_features.join(", ")}</p>
          ) : null}
          {productContext.target_users ? <p>Target users: {productContext.target_users}</p> : null}
          {productContext.known_limitations?.length ? (
            <p>Limitations: {productContext.known_limitations.join(", ")}</p>
          ) : null}
          <button
            type="button"
            onClick={startEditContext}
            className="mt-2 rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
          >
            Edit
          </button>
        </div>
      )}
    </section>
  );
}
