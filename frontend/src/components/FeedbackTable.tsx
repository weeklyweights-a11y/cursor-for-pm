import { Link } from "react-router-dom";
import type { FeedbackItem } from "../types/feedback";

function truncate(s: string, max: number) {
  if (s.length <= max) return s;
  return s.slice(0, max) + "\u2026";
}

function SourceBadge({ sourceType }: { sourceType: string }) {
  const style = sourceType === "slack" ? "bg-purple-100 text-purple-800" : sourceType === "csv" ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-800";
  return <span className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${style}`}>{sourceType}</span>;
}

function TopicBadge({ topic }: { topic: string | null | undefined }) {
  if (!topic) return null;
  return <span className="inline-flex rounded px-2 py-0.5 text-xs font-medium bg-slate-100 text-slate-800">{topic}</span>;
}

function UrgencyBadge({ urgency }: { urgency: string | null | undefined }) {
  if (!urgency) return null;
  const style = urgency === "critical" ? "bg-red-100 text-red-800" : urgency === "high" ? "bg-orange-100 text-orange-800" : urgency === "medium" ? "bg-amber-100 text-amber-800" : "bg-gray-100 text-gray-700";
  return <span className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${style}`}>{urgency}</span>;
}

function SentimentBadge({ sentiment }: { sentiment: string | null | undefined }) {
  if (!sentiment) return null;
  const style = sentiment === "positive" ? "text-green-700" : sentiment === "negative" ? "text-red-700" : "text-gray-600";
  const label = sentiment === "positive" ? "\u2295" : sentiment === "negative" ? "\u2296" : "\u25CB";
  return <span className={`text-xs font-medium ${style}`} title={sentiment}>{label}</span>;
}

function ExtractionStatus({ status }: { status: string | null | undefined }) {
  if (!status) return null;
  if (status === "pending") return <span className="text-amber-600 text-xs" title="Processing">\u22EE</span>;
  if (status === "failed") return <span className="text-red-600 text-xs" title="Extraction failed">\u26A0</span>;
  return null;
}

export interface FeedbackTableProps {
  items: FeedbackItem[];
  onRemove: (itemId: string) => void;
  deletingId: string | null;
}

export function FeedbackTable({ items, onRemove, deletingId }: FeedbackTableProps) {
  return (
    <div className="overflow-x-auto border border-gray-200 rounded-lg">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Content</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Source</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Theme</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Topic</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Urgency</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Sentiment</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Customer</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Match</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Extraction</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Author</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Timestamp</th>
            <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase w-20">Actions</th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {items.map((item) => (
            <tr key={item.id} className="hover:bg-gray-50">
              <td className="px-4 py-2 text-sm text-gray-800">
                <Link to={`/feedback/${item.id}`} className="text-blue-600 hover:underline">
                  {truncate(item.content, 100)}
                </Link>
              </td>
              <td className="px-4 py-2"><SourceBadge sourceType={item.source_type} /></td>
              <td className="px-4 py-2 text-sm text-gray-600">
                {item.theme_name ? (
                  <Link to={`/themes/${item.theme_id}`} className="text-blue-600 hover:underline">{item.theme_name}</Link>
                ) : item.is_outlier ? (
                  <span className="text-amber-600">Outlier</span>
                ) : (
                  "\u2014"
                )}
              </td>
              <td className="px-4 py-2"><TopicBadge topic={item.topic} /></td>
              <td className="px-4 py-2"><UrgencyBadge urgency={item.urgency} /></td>
              <td className="px-4 py-2"><SentimentBadge sentiment={item.sentiment} /></td>
              <td className="px-4 py-2 text-sm text-gray-600">{item.customer_name || item.customer_domain || "\u2014"}</td>
              <td className="px-4 py-2 text-sm text-gray-600">{item.match_status || "\u2014"}</td>
              <td className="px-4 py-2"><ExtractionStatus status={item.extraction_status} /></td>
              <td className="px-4 py-2 text-sm text-gray-600">{item.author_name || item.author_email || "\u2014"}</td>
              <td className="px-4 py-2 text-sm text-gray-500">{item.timestamp ? new Date(item.timestamp).toLocaleString() : "\u2014"}</td>
              <td className="px-4 py-2">
                <button type="button" onClick={() => onRemove(item.id)} disabled={deletingId === item.id} className="text-sm text-red-600 hover:underline disabled:opacity-50" title="Remove feedback">
                  {deletingId === item.id ? "Removing\u2026" : "Remove"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
