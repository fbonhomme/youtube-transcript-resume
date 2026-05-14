import api from "./client";

export interface Theme {
  id: number;
  name: string;
  color: string;
  icon: string | null;
  created_at: string;
  summary_count: number;
}

export interface ThemeCreate {
  name: string;
  color?: string;
  icon?: string | null;
}

export const listThemes = () =>
  api.get<Theme[]>("/themes/").then((r) => r.data);

export const createTheme = (payload: ThemeCreate) =>
  api.post<Theme>("/themes/", payload).then((r) => r.data);

export const updateTheme = (id: number, payload: Partial<ThemeCreate>) =>
  api.put<Theme>(`/themes/${id}`, payload).then((r) => r.data);

export const deleteTheme = (id: number) =>
  api.delete(`/themes/${id}`);
