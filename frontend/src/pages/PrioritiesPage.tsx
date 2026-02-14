import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Layout } from "../components/Layout";
import { ScoringWeightsPanel } from "../components/ScoringWeightsPanel";
import { getThemes } from "../api/themes";
import { getClusteringStatus, runClustering, backfillEmbeddings } from "../api/clustering";
import type { Theme, ClusteringStatus } from "../types/themes";

export function PrioritiesPage() {
  const [themes, setThemes] = useState<Theme[]>([]);
  const [clustering, setClustering] = useState<ClusteringStatus | null>(null);
  const [reclusterLoading, setReclusterLoading] = useState(false);
  const [backfillLoading, setBackfillLoading] = useState(false);
  const [backfillMessage, setBackfillMessage] = useState<string | null>(null);

  const loadThemes = () => getThemes({ page: 1, page_size: 50, sort_by: "priority_score" }).then((r) => setThemes(r.data)).catch(() => setThemes([]));
  const loadClustering = () => getClusteringStatus().then(setClustering).catch(() => setClustering(null));

  useEffect(() => {
    loadThemes();
    loadClustering();
  }, []);

  const handleRecluster = async () => {
    setReclusterLoading(true);
    try {
      await runClustering();
      loadClustering();
      loadThemes();
    } finally {
      setReclusterLoading(false);
    }
  };

  const handleBackfillEmbeddings = async () => {
    setBackfillMessage(null);
    setBackfillLoading(true);
    try {
      const { enqueued } = await backfillEmbeddings();
      setBackfillMessage(enqueued > 0 ? `Enqueued ${enqueued} item(s). Wait a moment then refresh or Re-cluster.` : "No items needed embeddings.");
      loadClustering();
    } catch {
      setBackfillMessage("Failed to queue embeddings.");
    } finally {
      setBackfillLoading(false);
    }
  };

  return (
    <Layout>
      <div className="max-w-4xl mx-auto w-full">
        <h1 className="text-2xl font-semibold text-gray-800 mb-6">Your Priorities</h1>
        <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
            <h2 className="text-sm font-medium text-gray-700 mb-2">Clustering status</h2>
            {clustering ? (
              <p className="text-sm text-gray-600 mb-3">
                {clustering.last_run_at ? "Last run: " + new Date(clustering.last_run_at).toLocaleString() : "Not run yet"}
                {clustering.last_run_result && " — " + (clustering.last_run_result.clusters_found ?? 0) + " clusters, " + (clustering.last_run_result.outliers ?? 0) + " outliers"}
                <br />
                Items pending: {clustering.items_pending}
              </p>
            ) : (
              <p className="text-sm text-gray-500 mb-3">Loading...</p>
            )}
            <div className="flex flex-wrap gap-2 items-center">
              <button type="button" onClick={handleBackfillEmbeddings} disabled={backfillLoading} className="rounded bg-gray-600 px-3 py-1.5 text-sm text-white hover:bg-gray-700 disabled:opacity-50">
                {backfillLoading ? "Queuing..." : "Generate embeddings"}
              </button>
              <button type="button" onClick={handleRecluster} disabled={reclusterLoading || clustering?.is_running} className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50">
                {reclusterLoading || clustering?.is_running ? "Running..." : "Re-cluster"}
              </button>
            </div>
            {backfillMessage && <p className="text-xs text-gray-600 mt-2">{backfillMessage}</p>}
          </div>
          <ScoringWeightsPanel onApplied={loadThemes} />
        </div>
        <div className="space-y-4">
          {themes.length === 0 ? (
            <div className="rounded-lg border border-gray-200 bg-white p-8 text-center">
              <p className="text-gray-600">No themes yet. Run clustering when you have enough feedback with embeddings.</p>
            </div>
          ) : (
          themes.map((theme, idx) => (
            <div key={theme.id} className="border border-gray-200 rounded-lg p-4 bg-white hover:shadow-sm">
              <div className="flex justify-between items-start">
                <div>
                  <span className="text-sm font-medium text-gray-500 mr-2">#{idx + 1}</span>
                  <Link to={"/themes/" + theme.id} className="text-lg font-medium text-blue-600 hover:underline">{theme.name}</Link>
                  <p className="text-sm text-gray-600 mt-1">{theme.description || ""}</p>
                </div>
                <div className="text-right">
                  <span className="text-sm font-medium text-gray-700">Score: {(theme.priority_score * 100).toFixed(0)}%</span>
                  <div className="w-24 h-2 bg-gray-200 rounded mt-1 overflow-hidden">
                    <div className="h-full bg-blue-600 rounded" style={{ width: Math.min(100, theme.priority_score * 100) + "%" }} />
                  </div>
                </div>
              </div>
              <div className="mt-2 flex flex-wrap gap-2 text-xs text-gray-600">
                <span>{theme.mention_count} mentions</span>
                <span>{theme.unique_customers} customers</span>
                {theme.top_quotes?.slice(0, 2).map((q, i) => (
                  <span key={i} className="italic text-gray-500">"{q.slice(0, 60)}..."</span>
                ))}
              </div>
            </div>
          ))
        )}
        </div>
      </div>
    </Layout>
  );
}
