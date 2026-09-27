import api from "./client";

export interface LLMModel {
  id: string;
  label: string;
  provider: "anthropic" | "openrouter";
  input_price: number;
  output_price: number;
  available: boolean;
  is_default: boolean;
}

export const listModels = () => api.get<LLMModel[]>("/models/").then((r) => r.data);
