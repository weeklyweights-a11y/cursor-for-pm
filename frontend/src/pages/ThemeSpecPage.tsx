import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Layout } from "../components/Layout";
import { getCurrentBrief } from "../api/briefs";
import { getCurrentSpecForBrief } from "../api/specs";

export function ThemeSpecPage() {
  const { id: themeId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [briefId, setBriefId] = useState<string | null>(null);

  useEffect(() => {
    if (!themeId) return;
    getCurrentBrief(themeId)
      .then((brief) => {
        if (!brief) {
          setLoading(false);
          return;
        }
        setBriefId(brief.id);
        return getCurrentSpecForBrief(brief.id);
      })
      .then((spec) => {
        if (spec) {
          navigate(`/specs/${spec.id}`, { replace: true });
          return;
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [themeId, navigate]);

  if (!themeId) return null;
  if (loading) return <Layout><p className="text-gray-500">Loading…</p></Layout>;

  return (
    <Layout>
      <div className="max-w-lg mx-auto text-center py-12">
        <h2 className="text-xl font-semibold text-gray-800 mb-2">Implementation Spec</h2>
        <p className="text-gray-600 mb-6">
          No spec exists for this theme yet. Generate a brief, evaluate a solution, then generate a spec from the brief page.
        </p>
        {briefId && (
          <Link
            to={`/briefs/${briefId}`}
            className="inline-block rounded bg-blue-600 px-6 py-2 text-white hover:bg-blue-700"
          >
            Open Brief
          </Link>
        )}
      </div>
    </Layout>
  );
}
