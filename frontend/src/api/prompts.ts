import api from "./client";

export interface Prompt {
  id: number;
  name: string;
  description: string | null;
  system_prompt: string;
  is_default: boolean;
  created_at: string;
}

export interface PromptCreate {
  name: string;
  description?: string | null;
  system_prompt: string;
  is_default?: boolean;
}

export const listPrompts = () =>
  api.get<Prompt[]>("/prompts/").then((r) => r.data);

export const createPrompt = (payload: PromptCreate) =>
  api.post<Prompt>("/prompts/", payload).then((r) => r.data);

export const updatePrompt = (id: number, payload: Partial<PromptCreate>) =>
  api.put<Prompt>(`/prompts/${id}`, payload).then((r) => r.data);

export const deletePrompt = (id: number) =>
  api.delete(`/prompts/${id}`);
