import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Layout } from "../components/Layout";
import { useAuth } from "../context/authContext";
import { getOrganization } from "../api/organization";
import { getExtractionStats, getEnrichmentStats, extractPending } from "../api/feedback";
import { reEnrichUnmatched } from "../api/enrichment";
import { getTopCustomers } from "../api/customers";
import { getThemes } from "../api/themes";
import { getClusteringStatus } from "../api/clustering";
import type { Organization } from "../types/auth";
import type { ExtractionStats, EnrichmentStats } from "../types/feedback";
import type { TopCustomer } from "../types/customers";
import type { Theme, ClusteringStatus } from "../types/themes";

export function DashboardPage() {
  const { user } = useAuth();
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [extractionStats, setExtractionStats] = useState<ExtractionStats | null>(null);
  const [enrichmentStats, setEnrichmentStats] = useState<EnrichmentStats | null>(null);
  const [topCustomers, setTopCustomers] = useState<TopCustomer[]>([]);
  const [topThemes, setTopThemes] = useState<Theme[]>([]);
  const [clusteringStatus, setClusteringStatus] = useState<ClusteringStatus | null>(null);
  const [reEnriching, setReEnriching] = useState(false);
  const [extracting, setExtracting] = useState(false);

  useEffect(() => {
    getOrganization()
      .then(setOrganization)
      .catch(() => setOrganization(null));
  }, []);

  useEffect(() => {
    getExtractionStats()
      .then(setExtractionStats)
      .catch(() => setExtractionStats(null));
  }, []);

  useEffect(() => {
    getEnrichmentStats()
      .then(setEnrichmentStats)
      .catch(() => setEnrichmentStats(null));
  }, []);

  useEffect(() => {
    getTopCustomers(5)
      .then(setTopCustomers)
      .catch(() => setTopCustomers([]));
  }, []);

  useEffect(() => {
    getThemes({ page: 1, page_size: 5, sort_by: "priority_score" })
      .then((r) => setTopThemes(r.data))
      .catch(() => setTopThemes([]));
  }, []);

  useEffect(() => {
    getClusteringStatus()
      .then(setClusteringStatus)
      .catch(() => setClusteringStatus(null));
  }, []);

  const handleReEnrich = () => {
    setReEnriching(true);
    reEnrichUnmatched()
      .then((r) => { setEnrichmentStats((s) => s ? { ...s, unmatched: Math.max(0, s.unmatched - r.items_queued) } : null); })
      .catch(() => {})
      .finally(() => setReEnriching(false));
  };

  const handleExtractPending = () => {
    setExtracting(true);
    extractPending()
      .then((r) => {
        setExtractionStats((s) => s ? { ...s, pending: Math.max(0, s.pending - r.enqueued) } : null);
        getExtractionStats().then(setExtractionStats).catch(() => {});
      })
      .catch(() => {})
      .finally(() => setExtracting(false));
  };

  return (
    <Layout>
      <h1 className="text-2xl font-semibold text-gray-800 mb-2">Dashboard</h1>
      <p className="text-gray-600 mb-6">
        Welcome, {user?.name}
        {organization ? ` from ${organization.name}` : ""}.
      </p>
      <div className="flex flex-wrap gap-4">
        {extractionStats != null && (
          <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 max-w-md">
            <h2 className="text-lg font-medium text-gray-700 mb-2">Extraction stats</h2>
            <p className="text-sm text-gray-600 mb-2">
              <span className="font-medium text-green-700">{extractionStats.completed}</span> completed,
              {" "}<span className="font-medium text-amber-600">{extractionStats.pending}</span> pending,
              {" "}<span className="font-medium text-red-600">{extractionStats.failed}</span> failed
              {" "}out of {extractionStats.total} feedback items.
            </p>
            {extractionStats.pending > 0 && (
              <button
                type="button"
                onClick={handleExtractPending}
                disabled={extracting}
                className="text-sm text-blue-600 hover:underline disabled:opacity-50"
              >
                {extracting ? "Queuing…" : "Run extraction for pending"}
              </button>
            )}
          </div>
        )}
        {enrichmentStats != null && (
          <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 max-w-md">
            <h2 className="text-lg font-medium text-gray-700 mb-2">Enrichment stats</h2>
            <p className="text-sm text-gray-600 mb-2">
              <span className="font-medium text-green-700">{enrichmentStats.matched}</span> matched,
              {" "}<span className="font-medium text-amber-600">{enrichmentStats.pm_review}</span> in review,
              {" "}<span className="font-medium text-gray-600">{enrichmentStats.unmatched}</span> unmatched
              {" "}out of {enrichmentStats.total}.
            </p>
            <Link to="/customers" className="text-sm text-blue-600 hover:underline">Customers</Link>
            {" · "}
            <button type="button" onClick={handleReEnrich} disabled={reEnriching || enrichmentStats.unmatched === 0} className="text-sm text-blue-600 hover:underline disabled:opacity-50">
              {reEnriching ? "Queuing…" : "Re-enrich unmatched"}
            </button>
          </div>
        )}
        {topThemes.length > 0 && (
          <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 max-w-md">
            <h2 className="text-lg font-medium text-gray-700 mb-2">Top 5 Priorities</h2>
            <ul className="space-y-1">
              {topThemes.map((t) => (
                <li key={t.id} className="flex justify-between text-sm">
                  <Link to={`/themes/${t.id}`} className="text-blue-600 hover:underline">{t.name}</Link>
                  <span className="text-gray-600">{(t.priority_score * 100).toFixed(0)}%</span>
                </li>
              ))}
            </ul>
            <Link to="/priorities" className="text-sm text-blue-600 hover:underline">View all priorities</Link>
          </div>
        )}
        {clusteringStatus != null && (
          <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 max-w-md">
            <h2 className="text-lg font-medium text-gray-700 mb-2">Clustering Status</h2>
            <p className="text-sm text-gray-600 mb-1">
              {clusteringStatus.last_run_at ? "Last run: " + new Date(clusteringStatus.last_run_at).toLocaleString() : "Not run yet"}
            </p>
            {clusteringStatus.last_run_result && (
              <p className="text-sm text-gray-600 mb-1">
                {clusteringStatus.last_run_result.clusters_found ?? 0} clusters, {clusteringStatus.last_run_result.outliers ?? 0} outliers
              </p>
            )}
            <p className="text-sm text-gray-600 mb-2">Items pending: {clusteringStatus.items_pending}</p>
            <Link to="/priorities" className="text-sm text-blue-600 hover:underline">Priorities</Link>
          </div>
        )}
        {topCustomers.length > 0 && (
          <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 max-w-md">
            <h2 className="text-lg font-medium text-gray-700 mb-2">Top customers by feedback</h2>
            <ul className="space-y-1">
              {topCustomers.map((c) => (
                <li key={c.id} className="flex justify-between text-sm">
                  <Link to={`/customers/${c.id}`} className="text-blue-600 hover:underline">
                    {c.company_name || c.domain}
                  </Link>
                  <span className="text-gray-600">{c.feedback_count}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </Layout>
  );
}
