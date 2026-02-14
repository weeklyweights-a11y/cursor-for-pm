import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { Layout } from "../components/Layout";
import { getTheme, getThemeFeedback } from "../api/themes";
import type { Theme } from "../types/themes";
import type { FeedbackItem } from "../types/feedback";

export function ThemeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [theme, setTheme] = useState<Theme | null>(null);
  const [feedback, setFeedback] = useState<FeedbackItem[]>([]);
  const [feedbackPage, setFeedbackPage] = useState(1);
  const [feedbackTotal, setFeedbackTotal] = useState(0);

  useEffect(() => {
    if (!id) return;
    getTheme(id).then(setTheme).catch(() => setTheme(null));
  }, [id]);

  useEffect(() => {
    if (!id) return;
    getThemeFeedback(id, { page: feedbackPage, page_size: 20 }).then((r) => {
      setFeedback(r.data);
      setFeedbackTotal(r.pagination.total);
    }).catch(() => setFeedback([]));
  }, [id, feedbackPage]);

  if (!id) return null;
  if (!theme) return <Layout><p className="text-gray-500">Loading\u2026</p></Layout>;

  const breakdown = theme.score_breakdown || {};
  const totalPages = Math.max(1, Math.ceil(feedbackTotal / 20));

  return (
    <Layout>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-800">{theme.name}</h1>
        <p className="text-gray-600 mt-1">{theme.description || ""}</p>
        <p className="text-sm text-gray-500 mt-2">
          Priority score: {(theme.priority_score * 100).toFixed(0)}% · {theme.mention_count} mentions · {theme.unique_customers} unique customers
        </p>
      </div>

      {Object.keys(breakdown).length > 0 && (
        <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 mb-6">
          <h2 className="text-lg font-medium text-gray-700 mb-2">Score breakdown</h2>
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-gray-600">
                <th className="py-1 pr-4">Factor</th>
                <th className="py-1 pr-4">Raw</th>
                <th className="py-1 pr-4">Normalized</th>
                <th className="py-1">Weighted</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(breakdown).map(([key, v]) => (
                <tr key={key}>
                  <td className="py-1 pr-4 capitalize">{key.replace("_", " ")}</td>
                  <td className="py-1 pr-4">{v?.raw != null ? v.raw : "\u2014"}</td>
                  <td className="py-1 pr-4">{v?.normalized != null ? (v.normalized * 100).toFixed(0) + "%" : "\u2014"}</td>
                  <td className="py-1">{(v?.weighted != null ? v.weighted * 100 : 0).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {theme.top_quotes && theme.top_quotes.length > 0 && (
        <div className="border border-gray-200 rounded-lg p-4 mb-6">
          <h2 className="text-lg font-medium text-gray-700 mb-2">Top quotes</h2>
          <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
            {theme.top_quotes.map((q, i) => (
              <li key={i}>"{q}"</li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <h2 className="text-lg font-medium text-gray-700 mb-2">Feedback in this theme</h2>
        {feedback.length === 0 ? (
          <p className="text-gray-500">No feedback in this theme.</p>
        ) : (
          <>
            <ul className="space-y-2">
              {feedback.map((item) => (
                <li key={item.id} className="border border-gray-200 rounded p-2 bg-white">
                  <Link to={`/feedback/${item.id}`} className="text-blue-600 hover:underline">
                    {item.content?.slice(0, 150)}{item.content && item.content.length > 150 ? "\u2026" : ""}
                  </Link>
                </li>
              ))}
            </ul>
            {totalPages > 1 && (
              <div className="mt-4 flex gap-2">
                <button type="button" onClick={() => setFeedbackPage((p) => Math.max(1, p - 1))} disabled={feedbackPage <= 1} className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50">Previous</button>
                <span className="text-sm text-gray-600">Page {feedbackPage} of {totalPages}</span>
                <button type="button" onClick={() => setFeedbackPage((p) => Math.min(totalPages, p + 1))} disabled={feedbackPage >= totalPages} className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50">Next</button>
              </div>
            )}
          </>
        )}
      </div>
    </Layout>
  );
}
