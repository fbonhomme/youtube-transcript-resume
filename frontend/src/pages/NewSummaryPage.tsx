import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { createSummary } from "../api/summaries";
import { listThemes } from "../api/themes";
import { listPrompts } from "../api/prompts";
import styles from "./NewSummaryPage.module.css";

const LANGUAGES = [
  { value: "fr", label: "Français" },
  { value: "en", label: "English" },
  { value: "es", label: "Español" },
  { value: "de", label: "Deutsch" },
  { value: "it", label: "Italiano" },
  { value: "pt", label: "Português" },
  { value: "ja", label: "日本語" },
  { value: "zh", label: "中文" },
];

export default function NewSummaryPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [url, setUrl] = useState("");
  const [language, setLanguage] = useState("fr");
  const [themeId, setThemeId] = useState<number | null>(null);
  const [promptId, setPromptId] = useState<number | null>(null);
  const [tagInput, setTagInput] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [elapsed, setElapsed] = useState(0);
  const abortRef = useRef<AbortController | null>(null);

  const { data: themes = [] } = useQuery({ queryKey: ["themes"], queryFn: listThemes });
  const { data: prompts = [] } = useQuery({ queryKey: ["prompts"], queryFn: listPrompts });

  const mutation = useMutation({
    mutationFn: (payload: Parameters<typeof createSummary>[0]) => {
      const controller = new AbortController();
      abortRef.current = controller;
      return createSummary(payload, controller.signal);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["summaries"] });
      navigate(`/library/${data.id}`);
    },
    onError: (err: unknown) => {
      if (axios.isCancel(err)) { setError(""); return; }
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Une erreur est survenue.");
    },
  });

  useEffect(() => {
    if (!mutation.isPending) { setElapsed(0); return; }
    const start = Date.now();
    const id = setInterval(() => setElapsed(Math.round((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(id);
  }, [mutation.isPending]);

  const stage = elapsed < 8
    ? "Récupération du transcript…"
    : "Génération de la synthèse par IA…";

  const handleCancel = () => abortRef.current?.abort();

  const addTag = () => {
    const t = tagInput.trim();
    if (t && !tags.includes(t)) setTags([...tags, t]);
    setTagInput("");
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!url.trim()) { setError("Veuillez saisir une URL YouTube."); return; }
    mutation.mutate({ url: url.trim(), language, theme_id: themeId, prompt_id: promptId, tags });
  };

  const defaultPrompt = prompts.find((p) => p.is_default);

  return (
    <div className={styles.wrap}>
      <div className={styles.heading}>
        <h1 className={`${styles.title} u-lime-title`}>Nouvelle synthèse</h1>
        <p className={styles.subtitle}>Collez une URL YouTube pour générer une synthèse structurée par IA.</p>
      </div>

      <form onSubmit={handleSubmit}>
        <div className={styles.urlBlock}>
          <label className={styles.urlLabel} htmlFor="url">URL YouTube</label>
          <input
            id="url"
            name="url"
            type="url"
            placeholder="https://www.youtube.com/watch?v=..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className={styles.urlInput}
            disabled={mutation.isPending}
          />
        </div>

        <div className={`${styles.optionsCard} u-glow-surface`}>
          <div className={styles.row}>
            <div className={styles.field}>
              <span className={styles.fieldLabel}>Langue</span>
              <select
                name="language"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className={styles.select}
                disabled={mutation.isPending}
              >
                {LANGUAGES.map((l) => (
                  <option key={l.value} value={l.value}>{l.label}</option>
                ))}
              </select>
            </div>

            <div className={styles.field}>
              <span className={styles.fieldLabel}>Thème</span>
              <select
                name="theme"
                value={themeId ?? ""}
                onChange={(e) => setThemeId(e.target.value ? Number(e.target.value) : null)}
                className={styles.select}
                disabled={mutation.isPending}
              >
                <option value="">— Aucun —</option>
                {themes.map((t) => (
                  <option key={t.id} value={t.id}>{t.icon ? `${t.icon} ` : ""}{t.name}</option>
                ))}
              </select>
            </div>

            <div className={styles.field}>
              <span className={styles.fieldLabel}>Prompt</span>
              <select
                name="prompt"
                value={promptId ?? ""}
                onChange={(e) => setPromptId(e.target.value ? Number(e.target.value) : null)}
                className={styles.select}
                disabled={mutation.isPending}
              >
                <option value="">
                  {defaultPrompt ? "— Prompt par défaut —" : "— Intégré —"}
                </option>
                {prompts.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}{p.is_default ? " ✓" : ""}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className={styles.tagSection}>
            <span className={styles.fieldLabel}>Tags</span>
            <div className={styles.tagRow}>
              <input
                name="tag-input"
                type="text"
                placeholder="Ajouter un tag…"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTag(); } }}
                className={styles.tagInput}
                disabled={mutation.isPending}
              />
              <button type="button" className={styles.addBtn} onClick={addTag} disabled={mutation.isPending}>+</button>
            </div>
            {tags.length > 0 && (
              <div className={styles.tags}>
                {tags.map((t) => (
                  <span key={t} className={styles.tag}>
                    {t}
                    <button type="button" onClick={() => setTags(tags.filter((x) => x !== t))}>×</button>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {error && <p className={styles.error}>{error}</p>}

        <button type="submit" className={`${styles.submit} u-pill-btn`} disabled={mutation.isPending}>
          {mutation.isPending ? (
            <><span className={styles.spinner} /> Génération en cours…</>
          ) : "Générer la synthèse"}
        </button>

        {mutation.isPending && (
          <div className={styles.progress} role="status" aria-live="polite">
            <div className={styles.progressBar}><div className={styles.progressFill} /></div>
            <div className={styles.progressRow}>
              <span className={styles.stage}>{stage}</span>
              <span className={styles.elapsed}>{elapsed}s</span>
            </div>
            <p className={styles.hint}>La synthèse peut prendre 30 à 60 secondes selon la durée de la vidéo.</p>
            <button type="button" className={styles.cancelBtn} onClick={handleCancel}>Annuler</button>
          </div>
        )}
      </form>
    </div>
  );
}
