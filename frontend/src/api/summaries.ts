import api from "./client";
import type { Theme } from "./themes";

export interface Section {
  title: string;
  content: string;
}

export interface SummaryListItem {
  id: number;
  title: string;
  youtube_url: string;
  youtube_id: string;
  language: string;
  summary_short: string;
  key_points: string[];
  tags: string[];
  duration_read: number;
  feedback: number | null;
  theme_id: number | null;
  theme: Theme | null;
  created_at: string;
}

export interface SummaryOut extends SummaryListItem {
  summary_long: string;
  sections: Section[];
  transcript: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
}

export interface SummarizeRequest {
  url: string;
  language?: string;
  theme_id?: number | null;
  prompt_id?: number | null;
  tags?: string[];
}

export interface SearchResult {
  items: SummaryListItem[];
  total: number;
}

export const createSummary = (payload: SummarizeRequest, signal?: AbortSignal) =>
  api.post<SummaryOut>("/summaries/", payload, { signal }).then((r) => r.data);

export const listSummaries = (params?: { theme_id?: number; skip?: number; limit?: number }) =>
  api.get<SummaryListItem[]>("/summaries/", { params }).then((r) => r.data);

export const getSummary = (id: number) =>
  api.get<SummaryOut>(`/summaries/${id}`).then((r) => r.data);

export const updateSummary = (
  id: number,
  payload: { theme_id?: number | null; tags?: string[]; feedback?: number | null },
) => api.patch<SummaryOut>(`/summaries/${id}`, payload).then((r) => r.data);

export const deleteSummary = (id: number) =>
  api.delete(`/summaries/${id}`);

export const searchSummaries = (params: { q?: string; theme_id?: number; skip?: number; limit?: number }) =>
  api.get<SearchResult>("/search/", { params }).then((r) => r.data);

export interface ImportPreviewItem {
  url: string;
  video_id: string;
  title: string;
  already_imported: boolean;
  error: string | null;
}

export interface ImportPreviewResult {
  items: ImportPreviewItem[];
}

export const importPreview = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return api
    .post<ImportPreviewResult>("/summaries/import/preview", form, {
      headers: { "Content-Type": "multipart/form-data" },
    })
    .then((r) => r.data);
};

export const exportSummariesUrl = (themeId?: number | null) =>
  themeId ? `/summaries/export?theme_id=${themeId}` : "/summaries/export";
