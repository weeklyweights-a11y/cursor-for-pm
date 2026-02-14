import { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { getFeedbackItem, manualMatchFeedback, deleteFeedback } from "../api/feedback";
import { getCustomers } from "../api/customers";
import type { FeedbackItem } from "../types/feedback";
import type { Customer } from "../types/customers";

export function FeedbackDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [item, setItem] = useState<FeedbackItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [customerSearch, setCustomerSearch] = useState("");
  const [customerResults, setCustomerResults] = useState<Customer[]>([]);
  const [matching, setMatching] = useState(false);
  const [matchError, setMatchError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  const loadItem = () => {
    if (!id) return;
    getFeedbackItem(id)
      .then(setItem)
      .catch(() => setItem(null))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (id) setLoading(true);
    loadItem();
  }, [id]);

  useEffect(() => {
    if (!customerSearch.trim()) {
      setCustomerResults([]);
      return;
    }
    getCustomers({ search: customerSearch.trim(), page_size: 20 })
      .then((res) => setCustomerResults(res.data))
      .catch(() => setCustomerResults([]));
  }, [customerSearch]);

  const handleManualMatch = (customerId: string) => {
    if (!id) return;
    setMatching(true);
    setMatchError(null);
    manualMatchFeedback(id, customerId)
      .then((updated) => { setItem(updated); setCustomerSearch(""); setCustomerResults([]); })
      .catch((err) => setMatchError(err.response?.data?.error?.message || "Match failed"))
      .finally(() => setMatching(false));
  };

  const handleDelete = () => {
    if (!id) return;
    setDeleting(true);
    deleteFeedback(id)
      .then(() => navigate("/feedback"))
      .catch(() => setDeleting(false));
  };

  if (loading) return <Layout><p className="text-gray-500">Loading...</p></Layout>;
  if (!item) return <Layout><p className="text-red-600">Feedback not found.</p></Layout>;

  return (
    <Layout>
      <div className="mb-4 flex justify-between items-center">
        <Link to="/feedback" className="text-sm text-blue-600 hover:underline">← Back to Feedback</Link>
        <div className="flex items-center gap-2">
          {!deleteConfirm ? (
            <button
              type="button"
              onClick={() => setDeleteConfirm(true)}
              className="text-sm text-red-600 hover:underline"
            >
              Remove feedback
            </button>
          ) : (
            <>
              <span className="text-sm text-gray-600">Remove this item?</span>
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleting}
                className="rounded border border-red-600 bg-red-600 px-2 py-1 text-sm text-white hover:bg-red-700 disabled:opacity-50"
              >
                {deleting ? "Removing…" : "Yes, remove"}
              </button>
              <button
                type="button"
                onClick={() => setDeleteConfirm(false)}
                disabled={deleting}
                className="rounded border border-gray-300 px-2 py-1 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Cancel
              </button>
            </>
          )}
        </div>
      </div>
      <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
        <div>
          <span className="text-xs font-medium text-gray-500 uppercase">Source</span>
          <p><span className="inline-flex rounded px-2 py-0.5 text-xs font-medium bg-gray-100">{item.source_type}</span></p>
        </div>
        <div>
          <span className="text-xs font-medium text-gray-500 uppercase">Content</span>
          <p className="mt-1 text-gray-800 whitespace-pre-wrap">{item.content}</p>
        </div>
        {(item.pain_point ?? item.topic ?? item.urgency ?? item.sentiment ?? item.extraction_status) && (
          <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 space-y-3">
            <h3 className="text-sm font-medium text-gray-700 uppercase">Extracted signals</h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              {item.topic && <div><span className="text-gray-500">Topic</span><p>{item.topic}</p></div>}
              {item.pain_point && <div className="col-span-2"><span className="text-gray-500">Pain point</span><p>{item.pain_point}</p></div>}
              {item.related_feature && <div><span className="text-gray-500">Related feature</span><p>{item.related_feature}</p></div>}
              {item.is_existing_feature != null && <div><span className="text-gray-500">Existing feature</span><p>{item.is_existing_feature ? "Yes" : "No"}</p></div>}
              {item.feature_gap && <div className="col-span-2"><span className="text-gray-500">Feature gap</span><p>{item.feature_gap}</p></div>}
              {item.urgency && <div><span className="text-gray-500">Urgency</span><p>{item.urgency}</p></div>}
              {item.sentiment && <div><span className="text-gray-500">Sentiment</span><p>{item.sentiment}</p></div>}
              {item.extraction_confidence != null && <div><span className="text-gray-500">Confidence</span><p>{Math.round(item.extraction_confidence * 100)}%</p></div>}
              {item.extraction_status && <div><span className="text-gray-500">Status</span><p>{item.extraction_status}</p></div>}
            </div>
            {item.verbatim_quote && (
              <div className="mt-2 p-3 bg-white border border-gray-200 rounded callout">
                <span className="text-xs font-medium text-gray-500 uppercase">Verbatim quote</span>
                <p className="mt-1 text-gray-800 italic">&ldquo;{item.verbatim_quote}&rdquo;</p>
              </div>
            )}
          </div>
        )}
        {(item.customer_id ?? item.customer_name ?? item.match_status) && (
          <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
            <h3 className="text-sm font-medium text-gray-700 uppercase">Customer match</h3>
            <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
              {item.customer_name && <div><span className="text-gray-500">Customer</span><p><Link to={`/customers/${item.customer_id}`} className="text-blue-600 hover:underline">{item.customer_name}</Link></p></div>}
              {item.customer_domain && <div><span className="text-gray-500">Domain</span><p>{item.customer_domain}</p></div>}
              {item.segment && <div><span className="text-gray-500">Segment</span><p>{item.segment}</p></div>}
              {item.match_status && <div><span className="text-gray-500">Status</span><p>{item.match_status}</p></div>}
            </div>
          </div>
        )}
        {(!item.customer_id && (item.match_status === "unmatched" || item.match_status === "pm_review")) && (
          <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
            <h3 className="text-sm font-medium text-gray-700 uppercase mb-2">Match to customer</h3>
            <input
              type="text"
              placeholder="Search customers by domain or company..."
              value={customerSearch}
              onChange={(e) => setCustomerSearch(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm w-full max-w-md mb-2"
            />
            {matchError && <p className="text-sm text-red-600 mb-2">{matchError}</p>}
            {customerResults.length > 0 && (
              <ul className="border border-gray-200 rounded-md divide-y divide-gray-200 bg-white max-w-md max-h-48 overflow-auto">
                {customerResults.map((c) => (
                  <li key={c.id} className="px-3 py-2 flex justify-between items-center">
                    <span className="text-sm">{c.company_name || c.domain} ({c.domain})</span>
                    <button
                      type="button"
                      onClick={() => handleManualMatch(c.id)}
                      disabled={matching}
                      className="text-sm text-blue-600 hover:underline disabled:opacity-50"
                    >
                      {matching ? "Matching…" : "Select"}
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <p className="text-xs text-gray-500 mt-2">
              Or use <Link to="/review-queue" className="text-blue-600 hover:underline">Review queue</Link> or re-enrich.
            </p>
          </div>
        )}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Author name</span>
            <p>{item.author_name || "—"}</p>
          </div>
          <div>
            <span className="text-gray-500">Author email</span>
            <p>{item.author_email || "—"}</p>
          </div>
          <div>
            <span className="text-gray-500">Organization</span>
            <p>{item.organization_name || "—"}</p>
          </div>
          <div>
            <span className="text-gray-500">Timestamp</span>
            <p>{item.timestamp ? new Date(item.timestamp).toLocaleString() : "—"}</p>
          </div>
        </div>
        {item.metadata && Object.keys(item.metadata).length > 0 && (
          <div>
            <span className="text-xs font-medium text-gray-500 uppercase">Metadata</span>
            <pre className="mt-1 text-sm text-gray-600 bg-gray-50 p-2 rounded overflow-auto">
              {JSON.stringify(item.metadata, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </Layout>
  );
}
