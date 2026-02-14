import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Layout } from "../components/Layout";
import {
  getPendingReviews,
  confirmReview,
  rejectReview,
  skipReview,
} from "../api/review";
import type { ReviewQueueItem } from "../types/review";

export function ReviewQueuePage() {
  const [items, setItems] = useState<ReviewQueueItem[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [actingId, setActingId] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    getPendingReviews({ page, page_size: pageSize })
      .then((res) => {
        setItems(res.data);
        setTotal(res.pagination.total);
        setTotalPages(res.pagination.total_pages);
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [page, pageSize]);

  const handleConfirm = (reviewId: string) => {
    setActingId(reviewId);
    confirmReview(reviewId)
      .then(() => { setItems((prev) => prev.filter((r) => r.id !== reviewId)); setTotal((t) => Math.max(0, t - 1)); })
      .finally(() => setActingId(null));
  };

  const handleReject = (reviewId: string) => {
    setActingId(reviewId);
    rejectReview(reviewId)
      .then(() => { setItems((prev) => prev.filter((r) => r.id !== reviewId)); setTotal((t) => Math.max(0, t - 1)); })
      .finally(() => setActingId(null));
  };

  const handleSkip = (reviewId: string) => {
    setActingId(reviewId);
    skipReview(reviewId)
      .then(() => { setItems((prev) => prev.filter((r) => r.id !== reviewId)); setTotal((t) => Math.max(0, t - 1)); })
      .finally(() => setActingId(null));
  };

  return (
    <Layout>
      <h1 className="text-2xl font-semibold text-gray-800 mb-4">Review queue</h1>
      <p className="text-gray-600 mb-4">Confirm or reject suggested customer matches for feedback.</p>
      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : items.length === 0 ? (
        <p className="text-gray-500">No pending reviews.</p>
      ) : (
        <>
          <div className="space-y-4">
            {items.map((r) => (
              <div key={r.id} className="border border-gray-200 rounded-lg p-4 bg-white">
                <div className="grid grid-cols-2 gap-2 text-sm mb-3">
                  <div><span className="text-gray-500">Source domain</span><p className="font-medium">{r.source_domain}</p></div>
                  <div><span className="text-gray-500">Source company</span><p>{r.source_company_name || "—"}</p></div>
                  <div><span className="text-gray-500">Suggested customer</span><p>{r.candidate_customer_name || r.candidate_domain || "—"}</p></div>
                  <div><span className="text-gray-500">Confidence</span><p>{r.confidence != null ? `${Math.round(r.confidence * 100)}%` : "—"}</p></div>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleConfirm(r.id)}
                    disabled={actingId !== null}
                    className="rounded-md bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
                  >
                    Confirm
                  </button>
                  <button
                    type="button"
                    onClick={() => handleReject(r.id)}
                    disabled={actingId !== null}
                    className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                  >
                    Reject
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSkip(r.id)}
                    disabled={actingId !== null}
                    className="rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  >
                    Skip
                  </button>
                  <Link to={`/feedback/${r.feedback_item_id}`} className="text-blue-600 hover:underline text-sm self-center">View feedback</Link>
                </div>
              </div>
            ))}
          </div>
          {totalPages > 1 && (
            <div className="mt-4 flex items-center gap-2">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50"
              >
                Previous
              </button>
              <span className="text-sm text-gray-600">Page {page} of {totalPages} ({total} total)</span>
              <button
                type="button"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </Layout>
  );
}
