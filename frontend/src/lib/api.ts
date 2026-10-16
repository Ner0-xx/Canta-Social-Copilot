import type {
  AppSettings,
  ContentDraftData,
  ContentIdeaData,
  SourceData,
  SourceItemData,
  Strategy,
  AABExperimentData,
  WeeklyReportData,
  OAuthConnectionData,
  ScheduledJob,
} from "../types";

import { supabase } from "./supabase";

const API_BASE_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...init?.headers as Record<string, string>,
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const fullUrl = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;

  const response = await fetch(fullUrl, {
    ...init,
    headers,
  });

  if (!response.ok) {
    const errorBody = (await response.json().catch(() => null)) as
      | { detail?: string | Array<{ msg?: string }> }
      | null;
    const detail = errorBody?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg ?? "Invalid value").join(". ")
      : detail ?? `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export function getStrategy(): Promise<Strategy> {
  return request<Strategy>("/api/strategy");
}

export function saveStrategy(strategy: Strategy): Promise<Strategy> {
  return request<Strategy>("/api/strategy", {
    method: "PUT",
    body: JSON.stringify(strategy),
  });
}

export function getSettings(): Promise<AppSettings> {
  return request<AppSettings>("/api/settings");
}

export function saveSettings(settings: AppSettings): Promise<AppSettings> {
  return request<AppSettings>("/api/settings", {
    method: "PUT",
    body: JSON.stringify(settings),
  });
}

// Sources API
export function getSources(): Promise<SourceData[]> {
  return request<SourceData[]>("/api/sources");
}

export function createSource(payload: {
  name: string;
  source_type: string;
  uri_or_content: string;
}): Promise<SourceData> {
  return request<SourceData>("/api/sources", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getSourceItems(): Promise<SourceItemData[]> {
  return request<SourceItemData[]>("/api/sources/items");
}

export function syncSource(sourceId: number): Promise<SourceItemData[]> {
  return request<SourceItemData[]>(`/api/sources/${sourceId}/sync`, {
    method: "POST",
  });
}

export function deleteSource(sourceId: number): Promise<{ message: string; deleted_items: number }> {
  return request<{ message: string; deleted_items: number }>(`/api/sources/${sourceId}`, {
    method: "DELETE",
  });
}

// Ideas API
export function getIdeas(): Promise<ContentIdeaData[]> {
  return request<ContentIdeaData[]>("/api/content/ideas");
}

export function removeIdea(ideaId: number): Promise<{ archived: boolean }> {
  return request<{ archived: boolean }>(`/api/content/ideas/${ideaId}`, {
    method: "DELETE",
  });
}

export function generateIdeas(payload: {
  source_item_id?: number;
  topic_title?: string;
  topic_content?: string;
}): Promise<ContentIdeaData[]> {
  return request<ContentIdeaData[]>("/api/content/ideas/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function generateDraftsForIdea(ideaId: number): Promise<ContentDraftData[]> {
  return request<ContentDraftData[]>(`/api/content/ideas/${ideaId}/generate-drafts`, {
    method: "POST",
  });
}

// Content Drafts API
export function getDrafts(): Promise<ContentDraftData[]> {
  return request<ContentDraftData[]>("/api/content/drafts");
}

export function deleteDraft(draftId: number): Promise<{ deleted: boolean }> {
  return request<{ deleted: boolean }>(`/api/content/drafts/${draftId}`, {
    method: "DELETE",
  });
}

export function updateDraftStatus(draftId: number, status: string): Promise<ContentDraftData> {
  return request<ContentDraftData>(`/api/content/drafts/${draftId}/transition`, {
    method: "POST",
    body: JSON.stringify({ status }),
  });
}

export function checkDraftQuality(draftId: number): Promise<{ score: number; warnings: string[] }> {
  return request<{ score: number; warnings: string[] }>(`/api/content/drafts/${draftId}/check`, {
    method: "POST",
  });
}

export function updateDraft(draftId: number, data: { title?: string; body?: string, image_path?: string, experiment_id?: number, experiment_variant?: string }): Promise<ContentDraftData> {
  return request<ContentDraftData>(`/api/content/drafts/${draftId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export type DraftImageUploadResult = {
  draft: ContentDraftData;
  storage: "supabase" | "local" | "local_fallback" | "unknown";
  notice: string;
};

export async function uploadDraftImage(
  draftId: number,
  file: File,
  onProgress: (percent: number) => void,
): Promise<DraftImageUploadResult> {
  const formData = new FormData();
  formData.append("file", file);

  const { data: { session } } = await supabase.auth.getSession();
  const xhr = new XMLHttpRequest();
  const result = new Promise<DraftImageUploadResult>((resolve, reject) => {
    xhr.open("POST", `${API_BASE_URL}/api/content/drafts/${draftId}/image`);
    if (session?.access_token) {
      xhr.setRequestHeader("Authorization", `Bearer ${session.access_token}`);
    }

    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) {
        onProgress(Math.max(1, Math.min(99, Math.floor((event.loaded / event.total) * 100))));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status < 200 || xhr.status >= 300) {
        let message = `Image upload failed (HTTP ${xhr.status}).`;
        try {
          const body = JSON.parse(xhr.responseText) as { detail?: string };
          if (body.detail) message = body.detail;
        } catch {
          // Keep the explicit HTTP error when the response isn't JSON.
        }
        reject(new Error(message));
        return;
      }

      try {
        const draft = JSON.parse(xhr.responseText) as ContentDraftData;
        resolve({
          draft,
          storage:
            (xhr.getResponseHeader("X-Image-Storage") as DraftImageUploadResult["storage"]) ??
            "unknown",
          notice:
            xhr.getResponseHeader("X-Image-Notice") ?? "Image upload completed successfully.",
        });
      } catch {
        reject(new Error("Image was stored, but Canta returned an invalid upload response."));
      }
    });
    xhr.addEventListener("error", () => reject(new Error("Could not reach Canta to upload the image.")));
    xhr.addEventListener("abort", () => reject(new Error("Image upload was cancelled.")));

    xhr.send(formData);
  });

  return result;
}

export function publishManual(draftId: number): Promise<ContentDraftData> {
  return request<ContentDraftData>(`/api/content/drafts/${draftId}/publish-manual`, {
    method: "POST",
  });
}

export function confirmManualXPublication(
  draftId: number,
  postUrl: string,
): Promise<{ draft_id: number; platform_post_id: string; platform_post_url: string }> {
  return request<{ draft_id: number; platform_post_id: string; platform_post_url: string }>(
    `/api/content/drafts/${draftId}/confirm-x-manual`,
    {
      method: "POST",
      body: JSON.stringify({ post_url: postUrl }),
    },
  );
}

export function getScheduledJobs(): Promise<ScheduledJob[]> {
  return request<ScheduledJob[]>("/api/schedule");
}

export function scheduleDraft(draftId: number, platform: string, scheduledAt: string): Promise<ScheduledJob> {
  return request<ScheduledJob>("/api/schedule", {
    method: "POST",
    body: JSON.stringify({ draft_id: draftId, platform, scheduled_at: scheduledAt }),
  });
}

export function cancelScheduledJob(jobId: number): Promise<{ message: string }> {
  return request<{ message: string }>(`/api/schedule/${jobId}`, {
    method: "DELETE",
  });
}

export function getOAuthStatus(platform: string): Promise<OAuthConnectionData> {
  return request<OAuthConnectionData>(`/api/oauth/${platform}/status`);
}

export function refreshXOAuth(): Promise<OAuthConnectionData> {
  return request<OAuthConnectionData>("/api/oauth/x/refresh", {
    method: "POST",
  });
}

export function disconnectOAuth(platform: string): Promise<{ disconnected: boolean; platform: string }> {
  return request<{ disconnected: boolean; platform: string }>(`/api/oauth/${platform}`, {
    method: "DELETE",
  });
}

export function connectOAuth(platform: string): void {
  window.location.href = `${API_BASE_URL}/api/oauth/${platform}/login`;
}

export function getExperiments(): Promise<AABExperimentData[]> {
  return request<AABExperimentData[]>("/api/analytics/experiments");
}

export function createExperiment(data: { name: string; hypothesis: string; end_date?: string }): Promise<AABExperimentData> {
  return request<AABExperimentData>("/api/analytics/experiments", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getWeeklyReports(): Promise<WeeklyReportData[]> {
  return request<WeeklyReportData[]>("/api/analytics/reports");
}
