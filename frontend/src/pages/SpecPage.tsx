import { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { useParams, Link } from "react-router-dom";
import { Layout } from "../components/Layout";
import {
  getSpec,
  getSpecStatus,
  getSpecsForBrief,
  editSpecSection,
  regenerateSpecSection,
  exportSpecMarkdown,
  exportSpecCursor,
} from "../api/specs";
import type { Spec, SpecSection as SpecSectionType } from "../types/specs";

const SECTION_ORDER = [
  "executive_summary",
  "background_evidence",
  "user_stories",
  "functional_requirements",
  "technical_guidance",
  "data_model_changes",
  "api_contracts",
  "testing_verification",
];

function SpecSectionCard({
  section,
  specId,
  onRegenerate,
  onEditDone,
  isRegenerating,
}: {
  section: SpecSectionType;
  specId: string;
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
            onClick={() => {
              onEditDone(section.key, editContent);
              setEditing(false);
            }}
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

export function SpecPage() {
  const { id } = useParams<{ id: string }>();
  const [spec, setSpec] = useState<Spec | null>(null);
  const [versions, setVersions] = useState<Spec[]>([]);
  const [regenerating, setRegenerating] = useState<string | null>(null);
  const [exportLoading, setExportLoading] = useState(false);

  const loadSpec = useCallback(() => {
    if (!id) return;
    getSpec(id).then(setSpec).catch(() => setSpec(null));
  }, [id]);

  useEffect(() => {
    loadSpec();
  }, [loadSpec]);

  useEffect(() => {
    if (!id || !spec) return;
    if (spec.status === "generating") {
      const t = setInterval(() => {
        getSpecStatus(id).then((s) => {
          setSpec((sp) => (sp ? { ...sp, status: s.status } : null));
          if (s.status !== "generating") loadSpec();
        }).catch(() => clearInterval(t));
      }, 3000);
      return () => clearInterval(t);
    }
  }, [id, spec?.status, loadSpec]);

  useEffect(() => {
    if (spec?.brief_id) {
      getSpecsForBrief(spec.brief_id).then(setVersions).catch(() => setVersions([]));
    }
  }, [spec?.brief_id]);

  const handleRegenerate = async (sectionKey: string) => {
    if (!id) return;
    setRegenerating(sectionKey);
    try {
      await regenerateSpecSection(id, sectionKey);
      loadSpec();
    } finally {
      setRegenerating(null);
    }
  };

  const handleEditDone = async (sectionKey: string, content: string) => {
    if (!id) return;
    await editSpecSection(id, sectionKey, content);
    loadSpec();
  };

  const handleExportMarkdown = async () => {
    if (!id) return;
    setExportLoading(true);
    try {
      const { markdown_content, filename } = await exportSpecMarkdown(id);
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

  const handleExportCursor = async () => {
    if (!id) return;
    setExportLoading(true);
    try {
      const { markdown_content, filename } = await exportSpecCursor(id);
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
  if (!spec) return <Layout><p className="text-gray-500">Loading…</p></Layout>;

  const sections = spec.sections || [];

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h1 className="text-2xl font-semibold text-gray-800">{spec.title}</h1>
            <p className="text-sm text-gray-500 mt-1">
              Version {spec.version} · {spec.scope} · {spec.target_audience} · {new Date(spec.created_at).toLocaleDateString()}
            </p>
          </div>
          <span
            className={`rounded px-2 py-1 text-sm ${
              spec.status === "completed"
                ? "bg-green-100 text-green-800"
                : spec.status === "failed"
                  ? "bg-red-100 text-red-800"
                  : "bg-amber-100 text-amber-800"
            }`}
          >
            {spec.status === "generating" ? "Generating…" : spec.status === "completed" ? "Ready" : spec.status}
          </span>
        </div>

        <div className="flex gap-2 mb-4">
          <span className="rounded bg-gray-100 text-gray-700 px-2 py-0.5 text-xs">{spec.scope}</span>
          <span className="rounded bg-gray-100 text-gray-700 px-2 py-0.5 text-xs">{spec.target_audience}</span>
          {spec.brief_id && (
            <Link to={`/briefs/${spec.brief_id}`} className="text-sm text-blue-600 hover:underline">
              View Brief
            </Link>
          )}
        </div>

        {versions.length > 1 && (
          <div className="mb-4">
            <label className="text-sm text-gray-600 mr-2">Version:</label>
            <select
              className="border border-gray-300 rounded px-2 py-1 text-sm"
              value={spec.id}
              onChange={(e) => window.location.assign(`/specs/${e.target.value}`)}
            >
              {versions.map((v) => (
                <option key={v.id} value={v.id}>
                  v{v.version} {v.is_current ? "(current)" : ""}
                </option>
              ))}
            </select>
          </div>
        )}

        {spec.status === "generating" && (
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
              <SpecSectionCard
                key={sec.key}
                section={sec}
                specId={id}
                onRegenerate={handleRegenerate}
                onEditDone={handleEditDone}
                isRegenerating={regenerating}
              />
            );
          })}
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleExportMarkdown}
            disabled={exportLoading}
            className="rounded bg-gray-700 px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            {exportLoading ? "Exporting…" : "Export Markdown"}
          </button>
          <button
            type="button"
            onClick={handleExportCursor}
            disabled={exportLoading}
            className="rounded bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            Export for Cursor
          </button>
        </div>
      </div>
    </Layout>
  );
}
