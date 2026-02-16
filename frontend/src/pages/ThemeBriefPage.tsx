import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { getCurrentBrief, generateBrief } from "../api/briefs";

export function ThemeBriefPage() {
  const { id: themeId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    if (!themeId) return;
    getCurrentBrief(themeId)
      .then((brief) => {
        if (brief) navigate(`/briefs/${brief.id}`, { replace: true });
        else setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [themeId, navigate]);

  const handleGenerate = async () => {
    if (!themeId) return;
    setGenerating(true);
    try {
      const { brief_id } = await generateBrief(themeId);
      navigate(`/briefs/${brief_id}`);
    } catch {
      setGenerating(false);
    }
  };

  if (!themeId) return null;
  if (loading) return <Layout><p className="text-gray-500">Loading…</p></Layout>;

  return (
    <Layout>
      <div className="max-w-lg mx-auto text-center py-12">
        <h2 className="text-xl font-semibold text-gray-800 mb-2">Evidence Brief</h2>
        <p className="text-gray-600 mb-6">No brief exists for this theme yet.</p>
        <button
          type="button"
          onClick={handleGenerate}
          disabled={generating}
          className="rounded bg-blue-600 px-6 py-2 text-white disabled:opacity-50"
        >
          {generating ? "Generating…" : "Generate Evidence Brief"}
        </button>
      </div>
    </Layout>
  );
}
