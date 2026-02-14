import { useState, useEffect } from "react";
import { getScoringConfig, updateScoringConfig } from "../api/scoring";
import type { ScoringConfig } from "../types/themes";

const DEFAULT_WEIGHTS = { weight_volume: 0.25, weight_reach: 0.2, weight_urgency: 0.25, weight_sentiment: 0.15, weight_strategic_fit: 0.15 };
const SEGMENT_OPTIONS = ["Enterprise", "Mid-Market", "SMB"];

function toPct(x: number): number {
  return Math.round(x * 100);
}
function fromPct(x: number): number {
  return x / 100;
}

export function ScoringSettings() {
  const [config, setConfig] = useState<ScoringConfig | null>(null);
  const [goals, setGoals] = useState<string[]>(["", "", "", "", ""]);
  const [segments, setSegments] = useState<string[]>([]);
  const [pctVolume, setPctVolume] = useState(25);
  const [pctReach, setPctReach] = useState(20);
  const [pctUrgency, setPctUrgency] = useState(25);
  const [pctSentiment, setPctSentiment] = useState(15);
  const [pctStrategic, setPctStrategic] = useState(15);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getScoringConfig()
      .then((c) => {
        setConfig(c);
        if (c.goals?.length) setGoals((prev) => [...c.goals!.slice(0, 5), ...prev.slice(c.goals!.length)].slice(0, 5));
        if (c.target_segments?.length) setSegments(c.target_segments);
        setPctVolume(toPct(c.weight_volume));
        setPctReach(toPct(c.weight_reach));
        setPctUrgency(toPct(c.weight_urgency));
        setPctSentiment(toPct(c.weight_sentiment));
        setPctStrategic(toPct(c.weight_strategic_fit));
      })
      .catch(() => setConfig(null));
  }, []);

  const sum = pctVolume + pctReach + pctUrgency + pctSentiment + pctStrategic;
  const resetDefaults = () => {
    setPctVolume(25);
    setPctReach(20);
    setPctUrgency(25);
    setPctSentiment(15);
    setPctStrategic(15);
  };

  const handleApply = async () => {
    if (Math.abs(sum - 100) > 1) {
      setError("Weights must sum to 100%");
      return;
    }
    setError(null);
    setSaving(true);
    try {
      const updated = await updateScoringConfig({
        goals: goals.map((g) => g.trim()).filter(Boolean) || null,
        target_segments: segments.length ? segments : null,
        weight_volume: fromPct(pctVolume),
        weight_reach: fromPct(pctReach),
        weight_urgency: fromPct(pctUrgency),
        weight_sentiment: fromPct(pctSentiment),
        weight_strategic_fit: fromPct(pctStrategic),
      });
      setConfig(updated);
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { detail?: string } } };
      setError(ax?.response?.data?.detail ?? "Failed to save.");
    } finally {
      setSaving(false);
    }
  };

  const toggleSegment = (s: string) => {
    setSegments((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]));
  };

  return (
    <section className="mb-8">
      <h2 className="text-lg font-medium text-gray-700 mb-2">Scoring (Priorities)</h2>
      {error && <p className="text-sm text-red-600 mb-2">{error}</p>}
      <div className="space-y-4 max-w-xl">
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-1">Product goals (1–5)</h3>
          {[0, 1, 2, 3, 4].map((i) => (
            <input
              key={i}
              type="text"
              value={goals[i] ?? ""}
              onChange={(e) => setGoals((prev) => [...prev.slice(0, i), e.target.value, ...prev.slice(i + 1)].slice(0, 5))}
              placeholder={`Goal ${i + 1}`}
              className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm mb-1"
            />
          ))}
        </div>
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-1">Target segments</h3>
          <div className="flex gap-4">
            {SEGMENT_OPTIONS.map((s) => (
              <label key={s} className="flex items-center gap-1 text-sm">
                <input
                  type="checkbox"
                  checked={segments.includes(s)}
                  onChange={() => toggleSegment(s)}
                  className="rounded border-gray-300 text-blue-600"
                />
                {s}
              </label>
            ))}
          </div>
        </div>
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-1">Weights (sum = 100%)</h3>
          <p className="text-xs text-gray-500 mb-1">Sum: {sum}%</p>
          <div className="space-y-1 text-sm">
            <div className="flex items-center gap-2">
              <span className="w-28">Volume</span>
              <input
                type="range"
                min={0}
                max={100}
                value={pctVolume}
                onChange={(e) => setPctVolume(Number(e.target.value))}
                className="flex-1"
              />
              <span>{pctVolume}%</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-28">Reach</span>
              <input type="range" min={0} max={100} value={pctReach} onChange={(e) => setPctReach(Number(e.target.value))} className="flex-1" />
              <span>{pctReach}%</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-28">Urgency</span>
              <input type="range" min={0} max={100} value={pctUrgency} onChange={(e) => setPctUrgency(Number(e.target.value))} className="flex-1" />
              <span>{pctUrgency}%</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-28">Sentiment</span>
              <input type="range" min={0} max={100} value={pctSentiment} onChange={(e) => setPctSentiment(Number(e.target.value))} className="flex-1" />
              <span>{pctSentiment}%</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-28">Strategic fit</span>
              <input type="range" min={0} max={100} value={pctStrategic} onChange={(e) => setPctStrategic(Number(e.target.value))} className="flex-1" />
              <span>{pctStrategic}%</span>
            </div>
          </div>
          <div className="flex gap-2 mt-2">
            <button type="button" onClick={resetDefaults} className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50">
              Reset defaults
            </button>
            <button type="button" onClick={handleApply} disabled={saving || Math.abs(sum - 100) > 1} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
              {saving ? "Saving..." : "Apply"}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
