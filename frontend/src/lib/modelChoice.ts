import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listModels } from "../api/models";
import type { LLMModel } from "../api/models";

const STORAGE_KEY = "yt-summaries.model";

function readStored(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeStored(id: string) {
  try {
    localStorage.setItem(STORAGE_KEY, id);
  } catch {
    // stockage indisponible (navigation privée…) : le choix ne sera pas mémorisé
  }
}

// Modèle mémorisé s'il est toujours proposé et disponible, sinon le défaut.
export function resolveModel(models: LLMModel[], stored: string | null): string | undefined {
  const usable = models.filter((m) => m.available);
  return (usable.find((m) => m.id === stored) ?? usable.find((m) => m.is_default) ?? usable[0])?.id;
}

export function useModelChoice() {
  const { data: models = [] } = useQuery({ queryKey: ["models"], queryFn: listModels });
  const [stored, setStored] = useState<string | null>(readStored);
  const setModel = (id: string) => {
    setStored(id);
    writeStored(id);
  };
  return { models, model: resolveModel(models, stored), setModel };
}

export const formatPrice = (m: LLMModel) =>
  `${m.input_price.toLocaleString("fr-FR")} $ / ${m.output_price.toLocaleString("fr-FR")} $ par M tokens`;
