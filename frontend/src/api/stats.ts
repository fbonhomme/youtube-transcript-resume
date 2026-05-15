import api from "./client";

export interface Stats {
  total_summaries: number;
  total_cost_usd: number;
  total_input_tokens: number;
  total_output_tokens: number;
}

export const getStats = () => api.get<Stats>("/stats/").then((r) => r.data);
