import type { ScoreKey, SortKey } from "../api/summaries";

// Libellés des notes Jev (0 = premier niveau, 3 = dernier), alignés sur
// SCORE_CRITERIA dans backend/services/evaluator.py.
export const SCORE_LABELS: Record<ScoreKey, { label: string; levels: [string, string, string, string] }> = {
  densite: { label: "Densité", levels: ["Remplissage", "Quelques idées", "Riche", "Très dense"] },
  niveau: { label: "Niveau", levels: ["Grand public", "Intermédiaire", "Avancé", "Expert"] },
  actionnable: { label: "Actionnable", levels: ["Informatif", "Quelques conseils", "Concret", "Pas-à-pas"] },
  perennite: { label: "Pérennité", levels: ["Éphémère", "Quelques mois", "~1 an", "Intemporel"] },
};

export const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: "recent", label: "Plus récentes" },
  { value: "top", label: "Meilleures (notes + likes)" },
  { value: "densite", label: "Plus denses" },
  { value: "actionnable", label: "Plus actionnables" },
  { value: "perennite", label: "Plus intemporelles" },
  { value: "niveau", label: "Plus avancées" },
];

export const levelLabel = (key: ScoreKey, score: number) =>
  SCORE_LABELS[key].levels[Math.min(3, Math.max(0, Math.round(score)))];
