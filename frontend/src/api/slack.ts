import type { SlackChannel, SlackConnectionStatus } from "../types/feedback";
import { apiClient } from "./client";

/** Backend returns OAuth URL in JSON so we can set window.location (avoids CORS when following redirect). */
export async function getSlackInstallUrl(): Promise<string> {
  const { data } = await apiClient.get<{ data: { url: string } }>("/api/v1/slack/install-url");
  return data.data.url;
}

export async function getSlackChannels(): Promise<SlackChannel[]> {
  const { data } = await apiClient.get<{ data: { id: string; name: string }[] }>("/api/v1/slack/channels");
  return data.data;
}

export async function setSlackChannels(channelIds: string[]): Promise<{ channels: string[] }> {
  const { data } = await apiClient.post<{ data: { channels: string[] } }>("/api/v1/slack/channels", {
    channel_ids: channelIds,
  });
  return data.data;
}

export async function getSlackStatus(): Promise<SlackConnectionStatus> {
  const { data } = await apiClient.get<{ data: SlackConnectionStatus }>("/api/v1/slack/status");
  return data.data;
}

export async function disconnectSlack(): Promise<{ disconnected: boolean }> {
  const { data } = await apiClient.delete<{ data: { disconnected: boolean } }>("/api/v1/slack/disconnect");
  return data.data;
}
