import { useState, useEffect } from "react";
import { getScoringConfig, updateScoringConfig, reScore } from "../api/scoring";

const DEFAULTS = { volume: 25, reach: 20, urgency: 25, sentiment: 15, strategic: 15 };

export function ScoringWeightsPanel({ onApplied }: { onApplied?: () => void }) {
  const [collapsed, setCollapsed] = useState(true);
  const [pctVolume, setPctVolume] = useState(DEFAULTS.volume);
  const [pctReach, setPctReach] = useState(DEFAULTS.reach);
  const [pctUrgency, setPctUrgency] = useState(DEFAULTS.urgency);
  const [pctSentiment, setPctSentiment] = useState(DEFAULTS.sentiment);
  const [pctStrategic, setPctStrategic] = useState(DEFAULTS.strategic);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getScoringConfig().then((c) => {
      setPctVolume(Math.round(c.weight_volume * 100));
      setPctReach(Math.round(c.weight_reach * 100));
      setPctUrgency(Math.round(c.weight_urgency * 100));
      setPctSentiment(Math.round(c.weight_sentiment * 100));
      setPctStrategic(Math.round(c.weight_strategic_fit * 100));
    }).catch(() => {});
  }, []);

  const sum = pctVolume + pctReach + pctUrgency + pctSentiment + pctStrategic;
  const reset = () => {
    setPctVolume(DEFAULTS.volume);
    setPctReach(DEFAULTS.reach);
    setPctUrgency(DEFAULTS.urgency);
    setPctSentiment(DEFAULTS.sentiment);
    setPctStrategic(DEFAULTS.strategic);
  };

  const apply = async () => {
    if (Math.abs(sum - 100) > 1) return;
    setSaving(true);
    try {
      await updateScoringConfig({
        weight_volume: pctVolume / 100,
        weight_reach: pctReach / 100,
        weight_urgency: pctUrgency / 100,
        weight_sentiment: pctSentiment / 100,
        weight_strategic_fit: pctStrategic / 100,
      });
      await reScore();
      onApplied?.();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="border border-gray-200 rounded-lg bg-gray-50 overflow-hidden">
      <button type="button" onClick={() => setCollapsed(!collapsed)} className="w-full px-4 py-2 text-left font-medium text-gray-700 flex justify-between items-center">
        Scoring weights
        <span>{collapsed ? "v" : "^"}</span>
      </button>
      {!collapsed && (
        <div className="px-4 pb-4 space-y-2">
          <p className="text-xs text-gray-500">Sum: {sum}%</p>
          {[
            { label: "Volume", value: pctVolume, set: setPctVolume },
            { label: "Reach", value: pctReach, set: setPctReach },
            { label: "Urgency", value: pctUrgency, set: setPctUrgency },
            { label: "Sentiment", value: pctSentiment, set: setPctSentiment },
            { label: "Strategic fit", value: pctStrategic, set: setPctStrategic },
          ].map((row) => (
            <div key={row.label} className="flex items-center gap-2 text-sm">
              <span className="w-24">{row.label}</span>
              <input type="range" min={0} max={100} value={row.value} onChange={(e) => row.set(Number(e.target.value))} className="flex-1" />
              <span>{row.value}%</span>
            </div>
          ))}
          <div className="flex gap-2 mt-2">
            <button type="button" onClick={reset} className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-100">Reset defaults</button>
            <button type="button" onClick={apply} disabled={saving || Math.abs(sum - 100) > 1} className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50">
              {saving ? "Saving..." : "Apply"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
