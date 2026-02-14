import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { Layout } from "../components/Layout";
import { getCustomer } from "../api/customers";
import { getFeedbackItems } from "../api/feedback";
import type { CustomerDetail } from "../types/customers";
import type { FeedbackItem } from "../types/feedback";

export function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [customer, setCustomer] = useState<CustomerDetail | null>(null);
  const [feedback, setFeedback] = useState<FeedbackItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getCustomer(id)
      .then(setCustomer)
      .catch(() => setCustomer(null))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!customer) return;
    getFeedbackItems({ page: 1, page_size: 50 })
      .then((res) => {
        const fromThisCustomer = res.data.filter((f) => f.customer_id === customer.id);
        setFeedback(fromThisCustomer);
      })
      .catch(() => setFeedback([]));
  }, [customer?.id]);

  if (loading) return <Layout><p className="text-gray-500">Loading...</p></Layout>;
  if (!customer) return <Layout><p className="text-red-600">Customer not found.</p></Layout>;

  return (
    <Layout>
      <div className="mb-4">
        <Link to="/customers" className="text-sm text-blue-600 hover:underline">← Back to Customers</Link>
      </div>
      <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-800">{customer.company_name || customer.domain}</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div><span className="text-gray-500">Domain</span><p className="font-medium">{customer.domain}</p></div>
          <div><span className="text-gray-500">Segment</span><p>{customer.segment || "—"}</p></div>
          <div><span className="text-gray-500">Feedback count</span><p>{customer.feedback_count}</p></div>
          <div><span className="text-gray-500">By source</span><p>{Object.entries(customer.feedback_by_source || {}).map(([k, v]) => `${k}: ${v}`).join(", ") || "—"}</p></div>
          {customer.latest_feedback_date && (
            <div><span className="text-gray-500">Latest feedback</span><p>{new Date(customer.latest_feedback_date).toLocaleString()}</p></div>
          )}
        </div>
        {feedback.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">Feedback from this customer</h3>
            <ul className="space-y-2">
              {feedback.slice(0, 20).map((f) => (
                <li key={f.id}>
                  <Link to={`/feedback/${f.id}`} className="text-blue-600 hover:underline text-sm">
                    {f.content.slice(0, 80)}…
                  </Link>
                </li>
              ))}
              {feedback.length > 20 && <li className="text-gray-500 text-sm">… and {feedback.length - 20} more</li>}
            </ul>
          </div>
        )}
      </div>
    </Layout>
  );
}
