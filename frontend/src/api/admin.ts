import api from "./client";

export interface ApiKeyStatus {
  provider: "anthropic" | "openrouter" | "ai_gateway";
  label: string;
  source: "interface" | "env" | "none";
  masked: string | null;
  unreadable: boolean;
}

export interface AdminKeys {
  encryption_ready: boolean;
  keys: ApiKeyStatus[];
}

export interface ApiKeyTestResult {
  ok: boolean;
  message: string;
}

export const getAdminKeys = () => api.get<AdminKeys>("/admin-api/keys/").then((r) => r.data);

export const saveApiKey = (provider: string, value: string) =>
  api.put<ApiKeyStatus>(`/admin-api/keys/${provider}`, { value }).then((r) => r.data);

export const deleteApiKey = (provider: string) =>
  api.delete<ApiKeyStatus>(`/admin-api/keys/${provider}`).then((r) => r.data);

export const testApiKey = (provider: string) =>
  api.post<ApiKeyTestResult>(`/admin-api/keys/${provider}/test`).then((r) => r.data);
