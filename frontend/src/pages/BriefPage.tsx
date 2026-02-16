import { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { useParams, Link } from "react-router-dom";
import { Layout } from "../components/Layout";
import {
  getBrief,
  getBriefStatus,
  getBriefsForTheme,
  editSection,
  regenerateSection,
  evaluateSolution,
  exportBriefMarkdown,
} from "../api/briefs";
import { getCurrentSpecForBrief } from "../api/specs";
import { SpecConfigModal } from "../components/SpecConfigModal";
import type { Brief, BriefSection as BriefSectionType } from "../types/briefs";
import type { Spec } from "../types/specs";

const SECTION_ORDER = [
  "problem_statement",
  "customer_impact",
  "evidence_summary",
  "trend_analysis",
  "business_case",
  "recommended_action",
  "risks",
];

function BriefSectionCard({
  section,
  briefId,
  onRegenerate,
  onEditDone,
  isRegenerating,
}: {
  section: BriefSectionType;
  briefId: string;
  onRegenerate: (key: string) => void;
  onEditDone: (key: string, content: string) => void;
  isRegenerating: string | null;
}) {
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState(section.content);

  const handleRevert = () => {
    const prev = section.edit_history?.slice(-1)[0];
    if (prev?.content != null) onEditDone(section.key, prev.content);
    setEditing(false);
  };

  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-white mb-4">
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-lg font-medium text-gray-800">{section.title}</h3>
        <div className="flex gap-2">
          {section.edited && (
            <button
              type="button"
              onClick={handleRevert}
              className="text-xs text-gray-500 hover:underline"
            >
              Revert
            </button>
          )}
          <button
            type="button"
            onClick={() => onRegenerate(section.key)}
            disabled={isRegenerating !== null}
            className="text-xs text-blue-600 hover:underline disabled:opacity-50"
          >
            {isRegenerating === section.key ? "Regenerating…" : "Regenerate"}
          </button>
          <button
            type="button"
            onClick={() => setEditing(!editing)}
            className="text-xs text-gray-600 hover:underline"
          >
            {editing ? "Cancel" : "Edit"}
          </button>
        </div>
      </div>
      {section.edited && (
        <span className="inline-block text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded mb-2">
          Edited
        </span>
      )}
      {editing ? (
        <>
          <textarea
            className="w-full border border-gray-300 rounded p-2 text-sm min-h-[120px]"
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
          />
          <button
            type="button"
            onClick={() => { onEditDone(section.key, editContent); setEditing(false); }}
            className="mt-2 rounded bg-blue-600 px-3 py-1 text-sm text-white"
          >
            Save
          </button>
        </>
      ) : (
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown>{section.content || "*Empty*"}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}

export function BriefPage() {
  const { id } = useParams<{ id: string }>();
  const [brief, setBrief] = useState<Brief | null>(null);
  const [versions, setVersions] = useState<Brief[]>([]);
  const [regenerating, setRegenerating] = useState<string | null>(null);
  const [solutionText, setSolutionText] = useState("");
  const [evalLoading, setEvalLoading] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [currentSpec, setCurrentSpec] = useState<Spec | null>(null);
  const [specConfigOpen, setSpecConfigOpen] = useState(false);

  const loadBrief = useCallback(() => {
    if (!id) return;
    getBrief(id).then(setBrief).catch(() => setBrief(null));
  }, [id]);

  useEffect(() => {
    loadBrief();
  }, [loadBrief]);

  useEffect(() => {
    if (!id || !brief) return;
    if (brief.status === "generating") {
      const t = setInterval(() => {
        getBriefStatus(id).then((s) => {
          setBrief((b) => (b ? { ...b, status: s.status } : null));
          if (s.status !== "generating") loadBrief();
        }).catch(() => clearInterval(t));
      }, 3000);
      return () => clearInterval(t);
    }
  }, [id, brief?.status, loadBrief]);

  useEffect(() => {
    if (brief?.theme_id) {
      getBriefsForTheme(brief.theme_id).then(setVersions).catch(() => setVersions([]));
    }
  }, [brief?.theme_id]);

  useEffect(() => {
    if (brief?.id && brief.status === "completed") {
      getCurrentSpecForBrief(brief.id).then(setCurrentSpec).catch(() => setCurrentSpec(null));
    } else {
      setCurrentSpec(null);
    }
  }, [brief?.id, brief?.status]);

  const handleRegenerate = async (sectionKey: string) => {
    if (!id) return;
    setRegenerating(sectionKey);
    try {
      await regenerateSection(id, sectionKey);
      loadBrief();
    } finally {
      setRegenerating(null);
    }
  };

  const handleEditDone = async (sectionKey: string, content: string) => {
    if (!id) return;
    await editSection(id, sectionKey, content);
    loadBrief();
  };

  const handleEvaluate = async () => {
    if (!id || !solutionText.trim()) return;
    setEvalLoading(true);
    try {
      await evaluateSolution(id, solutionText.trim());
      loadBrief();
    } finally {
      setEvalLoading(false);
    }
  };

  const handleExport = async () => {
    if (!id) return;
    setExportLoading(true);
    try {
      const { markdown_content, filename } = await exportBriefMarkdown(id);
      const blob = new Blob([markdown_content], { type: "text/markdown" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      a.click();
      URL.revokeObjectURL(a.href);
    } finally {
      setExportLoading(false);
    }
  };

  if (!id) return null;
  if (!brief) return <Layout><p className="text-gray-500">Loading…</p></Layout>;

  const sections = brief.sections || [];
  const ev = brief.solution_evaluation?.evaluation;

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h1 className="text-2xl font-semibold text-gray-800">{brief.title}</h1>
            <p className="text-sm text-gray-500 mt-1">
              Version {brief.version} · {new Date(brief.created_at).toLocaleDateString()}
            </p>
          </div>
          <span
            className={`rounded px-2 py-1 text-sm ${
              brief.status === "completed"
                ? "bg-green-100 text-green-800"
                : brief.status === "failed"
                  ? "bg-red-100 text-red-800"
                  : "bg-amber-100 text-amber-800"
            }`}
          >
            {brief.status === "generating" ? "Generating…" : brief.status === "completed" ? "Ready" : brief.status}
          </span>
        </div>

        {versions.length > 1 && (
          <div className="mb-4">
            <label className="text-sm text-gray-600 mr-2">Version:</label>
            <select
              className="border border-gray-300 rounded px-2 py-1 text-sm"
              value={brief.id}
              onChange={(e) => window.location.assign(`/briefs/${e.target.value}`)}
            >
              {versions.map((v) => (
                <option key={v.id} value={v.id}>
                  v{v.version} {v.is_current ? "(current)" : ""}
                </option>
              ))}
            </select>
          </div>
        )}

        {brief.status === "generating" && (
          <p className="text-sm text-gray-600 mb-4">
            Generating sections… Refresh or wait for auto-update.
          </p>
        )}

        <div className="mb-8">
          {SECTION_ORDER.map((key) => {
            const sec = sections.find((s) => s.key === key);
            if (!sec) {
              return (
                <div key={key} className="border border-gray-200 rounded-lg p-4 bg-gray-50 mb-4 animate-pulse">
                  <div className="h-4 bg-gray-200 rounded w-1/3 mb-2" />
                  <div className="h-20 bg-gray-200 rounded" />
                </div>
              );
            }
            return (
              <BriefSectionCard
                key={sec.key}
                section={sec}
                briefId={id}
                onRegenerate={handleRegenerate}
                onEditDone={handleEditDone}
                isRegenerating={regenerating}
              />
            );
          })}
        </div>

        <div className="border border-gray-200 rounded-lg p-4 bg-gray-50 mb-4">
          <h2 className="text-lg font-medium text-gray-800 mb-2">Evaluate a Solution</h2>
          <textarea
            className="w-full border border-gray-300 rounded p-2 text-sm min-h-[100px] mb-2"
            placeholder="Describe your proposed solution…"
            value={solutionText}
            onChange={(e) => setSolutionText(e.target.value)}
          />
          <button
            type="button"
            onClick={handleEvaluate}
            disabled={evalLoading || !solutionText.trim()}
            className="rounded bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            {evalLoading ? "Evaluating…" : "Evaluate"}
          </button>
          {ev && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <p className="text-sm font-medium text-gray-700">
                Coverage: {((ev.coverage_score ?? 0) * 100).toFixed(0)}% of pain points addressed
              </p>
              {ev.pain_points_addressed?.length ? (
                <ul className="list-disc list-inside text-sm text-gray-600 mt-2">
                  {ev.pain_points_addressed.map((p: { pain_point?: string; addressed?: boolean }, i: number) => (
                    <li key={i}>
                      {p.addressed ? "✓" : "✗"} {p.pain_point}
                    </li>
                  ))}
                </ul>
              ) : null}
              {ev.strengths?.length ? (
                <p className="text-sm mt-2"><strong>Strengths:</strong> {ev.strengths.join("; ")}</p>
              ) : null}
              {ev.gaps?.length ? (
                <p className="text-sm mt-1"><strong>Gaps:</strong> {ev.gaps.join("; ")}</p>
              ) : null}
            </div>
          )}
        </div>

        <div className="flex flex-wrap gap-2 items-center mb-4">
          <button
            type="button"
            onClick={handleExport}
            disabled={exportLoading}
            className="rounded bg-gray-700 px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            {exportLoading ? "Exporting…" : "Export as Markdown"}
          </button>

          <div className="border-l border-gray-300 pl-4">
            {!brief.solution_evaluation ? (
              <p className="text-sm text-amber-700">Evaluate a solution first to generate a spec.</p>
            ) : currentSpec ? (
              <div className="flex gap-2 items-center">
                <Link
                  to={`/specs/${currentSpec.id}`}
                  className="rounded bg-blue-600 px-4 py-2 text-sm text-white"
                >
                  View Spec
                </Link>
                <button
                  type="button"
                  onClick={() => setSpecConfigOpen(true)}
                  className="rounded border border-gray-300 px-4 py-2 text-sm text-gray-700"
                >
                  Generate New Spec
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setSpecConfigOpen(true)}
                className="rounded bg-blue-600 px-4 py-2 text-sm text-white"
              >
                Generate Spec
              </button>
            )}
          </div>
        </div>

        {specConfigOpen && id && (
          <SpecConfigModal briefId={id} onClose={() => setSpecConfigOpen(false)} />
        )}
      </div>
    </Layout>
  );
}
