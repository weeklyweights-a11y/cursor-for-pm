import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Layout } from "../components/Layout";
import { FeedbackTable } from "../components/FeedbackTable";
import { getFeedbackItems, deleteFeedback } from "../api/feedback";
import { getThemes } from "../api/themes";
import type { FeedbackItem } from "../types/feedback";
import type { Theme } from "../types/themes";

const SOURCE_OPTIONS = [{ value: "", label: "All" }, { value: "slack", label: "Slack" }, { value: "csv", label: "CSV" }, { value: "manual", label: "Manual" }];
const MATCH_STATUS_OPTIONS = [{ value: "", label: "All" }, { value: "matched", label: "Matched" }, { value: "auto_matched", label: "Auto-matched" }, { value: "pm_review", label: "PM review" }, { value: "unmatched", label: "Unmatched" }];
const SEGMENT_OPTIONS = [{ value: "", label: "All" }, { value: "smb", label: "SMB" }, { value: "mid_market", label: "Mid-Market" }, { value: "enterprise", label: "Enterprise" }, { value: "unmatched", label: "Unmatched" }];

export function FeedbackPage() {
  const [items, setItems] = useState<FeedbackItem[]>([]);
  const [themes, setThemes] = useState<Theme[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [sourceType, setSourceType] = useState("");
  const [matchStatus, setMatchStatus] = useState("");
  const [segment, setSegment] = useState("");
  const [themeId, setThemeId] = useState("");
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    getThemes({ page_size: 100 }).then((r) => setThemes(r.data)).catch(() => setThemes([]));
  }, []);

  const load = () => {
    setLoading(true);
    const isOutliers = themeId === "__outliers";
    const isUnclustered = themeId === "__unclustered";
    getFeedbackItems({
      page,
      page_size: pageSize,
      source_type: sourceType || undefined,
      match_status: matchStatus || undefined,
      segment: segment || undefined,
      theme_id: themeId && !isOutliers && !isUnclustered ? themeId : undefined,
      outliers_only: isOutliers,
      unclustered_only: isUnclustered,
    })
      .then((res) => {
        setItems(res.data);
        setTotal(res.pagination.total);
        setTotalPages(res.pagination.total_pages);
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [page, pageSize, sourceType, matchStatus, segment, themeId]);

  const handleRemove = (itemId: string) => {
    if (!window.confirm("Remove this feedback item? This cannot be undone.")) return;
    setDeletingId(itemId);
    deleteFeedback(itemId).then(load).finally(() => setDeletingId(null));
  };

  return (
    <Layout>
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-semibold text-gray-800">Feedback</h1>
        <div className="flex gap-2">
          <Link to="/feedback/upload" className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">Upload CSV</Link>
          <Link to="/feedback/add-manual" className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Add manually</Link>
        </div>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-4">
        <label htmlFor="sourceFilter" className="text-sm text-gray-700">Source:</label>
        <select id="sourceFilter" value={sourceType} onChange={(e) => { setSourceType(e.target.value); setPage(1); }} className="rounded-md border border-gray-300 px-3 py-1.5 text-sm">
          {SOURCE_OPTIONS.map((o) => <option key={o.value || "all"} value={o.value}>{o.label}</option>)}
        </select>
        <label htmlFor="matchStatusFilter" className="text-sm text-gray-700">Match:</label>
        <select id="matchStatusFilter" value={matchStatus} onChange={(e) => { setMatchStatus(e.target.value); setPage(1); }} className="rounded-md border border-gray-300 px-3 py-1.5 text-sm">
          {MATCH_STATUS_OPTIONS.map((o) => <option key={o.value || "all"} value={o.value}>{o.label}</option>)}
        </select>
        <label htmlFor="segmentFilter" className="text-sm text-gray-700">Segment:</label>
        <select id="segmentFilter" value={segment} onChange={(e) => { setSegment(e.target.value); setPage(1); }} className="rounded-md border border-gray-300 px-3 py-1.5 text-sm">
          {SEGMENT_OPTIONS.map((o) => <option key={o.value || "all"} value={o.value}>{o.label}</option>)}
        </select>
        <label htmlFor="themeFilter" className="text-sm text-gray-700">Theme:</label>
        <select id="themeFilter" value={themeId} onChange={(e) => { setThemeId(e.target.value); setPage(1); }} className="rounded-md border border-gray-300 px-3 py-1.5 text-sm">
          <option value="">All</option>
          {themes.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          <option value="__outliers">Outliers</option>
          <option value="__unclustered">Unclustered</option>
        </select>
      </div>

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : items.length === 0 ? (
        <p className="text-gray-500">No feedback yet. Upload a CSV or add manually.</p>
      ) : (
        <>
          <FeedbackTable items={items} onRemove={handleRemove} deletingId={deletingId} />
          {totalPages > 1 && (
            <div className="mt-4 flex items-center gap-2">
              <button type="button" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1} className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50">Previous</button>
              <span className="text-sm text-gray-600">Page {page} of {totalPages} ({total} total)</span>
              <button type="button" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page >= totalPages} className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50">Next</button>
            </div>
          )}
        </>
      )}
    </Layout>
  );
}
