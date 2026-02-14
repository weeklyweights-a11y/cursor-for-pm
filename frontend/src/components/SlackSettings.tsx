import { useState, useEffect } from "react";
import { getSlackInstallUrl, getSlackStatus, getSlackChannels, setSlackChannels, disconnectSlack } from "../api/slack";
import type { SlackChannel } from "../types/feedback";

export function SlackSettings() {
  const [connected, setConnected] = useState(false);
  const [teamName, setTeamName] = useState<string | null>(null);
  const [channels, setChannels] = useState<SlackChannel[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [savingChannels, setSavingChannels] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSlackStatus()
      .then((s) => {
        setConnected(s.connected);
        setTeamName(s.team_name);
        setSelectedIds(s.channels);
      })
      .catch(() => setConnected(false));
  }, []);

  useEffect(() => {
    if (connected) getSlackChannels().then(setChannels).catch(() => setChannels([]));
  }, [connected]);

  const handleConnectSlack = async () => {
    setError(null);
    try {
      const url = await getSlackInstallUrl();
      if (url) window.location.href = url;
      else setError("Could not start Slack connection.");
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { detail?: string } } };
      setError(ax?.response?.data?.detail ?? "Could not start Slack connection.");
    }
  };

  const handleDisconnect = async () => {
    setError(null);
    try {
      await disconnectSlack();
      setConnected(false);
      setTeamName(null);
      setSelectedIds([]);
      setChannels([]);
    } catch {
      setError("Failed to disconnect.");
    }
  };

  const handleSaveChannels = async () => {
    setError(null);
    setSavingChannels(true);
    try {
      await setSlackChannels(selectedIds);
    } catch {
      setError("Failed to save channels.");
    } finally {
      setSavingChannels(false);
    }
  };

  const toggleChannel = (id: string) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  return (
    <section className="mb-8">
      <h2 className="text-lg font-medium text-gray-700 mb-2">Slack</h2>
      {error && <p className="text-sm text-red-600 mb-2">{error}</p>}
      {!connected ? (
        <div>
          <p className="text-gray-600 mb-2">Connect your Slack workspace to import feedback from channels.</p>
          <button type="button" onClick={handleConnectSlack} className="rounded-md bg-[#4A154B] px-4 py-2 text-sm font-medium text-white hover:bg-[#5a1a5c]">
            Connect Slack
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <p className="text-gray-600">Connected to <strong>{teamName}</strong></p>
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-2">Monitored channels</h3>
            {channels.length === 0 ? (
              <p className="text-sm text-gray-500">Loading channels...</p>
            ) : (
              <ul className="border border-gray-200 rounded-lg divide-y divide-gray-200 max-h-48 overflow-y-auto">
                {channels.map((ch) => (
                  <li key={ch.id} className="flex items-center px-3 py-2">
                    <input type="checkbox" id={`ch-${ch.id}`} checked={selectedIds.includes(ch.id)} onChange={() => toggleChannel(ch.id)} className="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                    <label htmlFor={`ch-${ch.id}`} className="ml-2 text-sm text-gray-700">#{ch.name}</label>
                  </li>
                ))}
              </ul>
            )}
            <button type="button" onClick={handleSaveChannels} disabled={savingChannels} className="mt-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
              {savingChannels ? "Saving..." : "Save channels"}
            </button>
          </div>
          <button type="button" onClick={handleDisconnect} className="rounded-md border border-red-300 px-4 py-2 text-sm text-red-700 hover:bg-red-50">
            Disconnect Slack
          </button>
        </div>
      )}
    </section>
  );
}
