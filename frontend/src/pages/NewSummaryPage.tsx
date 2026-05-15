import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createSummary } from "../api/summaries";
import { listThemes } from "../api/themes";
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
  const [tagInput, setTagInput] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [error, setError] = useState("");

  const { data: themes = [] } = useQuery({ queryKey: ["themes"], queryFn: listThemes });

  const mutation = useMutation({
    mutationFn: createSummary,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["summaries"] });
      navigate(`/library/${data.id}`);
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Une erreur est survenue.");
    },
  });

  const addTag = () => {
    const t = tagInput.trim();
    if (t && !tags.includes(t)) setTags([...tags, t]);
    setTagInput("");
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!url.trim()) { setError("Veuillez saisir une URL YouTube."); return; }
    mutation.mutate({ url: url.trim(), language, theme_id: themeId, tags });
  };

  return (
    <div className={styles.wrap}>
      <h1 className={styles.title}>Nouvelle synthèse</h1>

      <form className={styles.form} onSubmit={handleSubmit}>
        <label className={styles.field}>
          <span>URL YouTube</span>
          <input
            name="url"
            type="url"
            placeholder="https://www.youtube.com/watch?v=..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className={styles.input}
            disabled={mutation.isPending}
          />
        </label>

        <div className={styles.row}>
          <label className={styles.field}>
            <span>Langue de sortie</span>
            <select
              name="language"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className={styles.input}
              disabled={mutation.isPending}
            >
              {LANGUAGES.map((l) => (
                <option key={l.value} value={l.value}>{l.label}</option>
              ))}
            </select>
          </label>

          <label className={styles.field}>
            <span>Thème (optionnel)</span>
            <select
              name="theme"
              value={themeId ?? ""}
              onChange={(e) => setThemeId(e.target.value ? Number(e.target.value) : null)}
              className={styles.input}
              disabled={mutation.isPending}
            >
              <option value="">— Aucun —</option>
              {themes.map((t) => (
                <option key={t.id} value={t.id}>{t.icon ? `${t.icon} ` : ""}{t.name}</option>
              ))}
            </select>
          </label>
        </div>

        <div className={styles.field}>
          <span>Tags</span>
          <div className={styles.tagRow}>
            <input
              name="tag-input"
              type="text"
              placeholder="Ajouter un tag…"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTag(); } }}
              className={styles.input}
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

        {error && <p className={styles.error}>{error}</p>}

        <button type="submit" className={styles.submit} disabled={mutation.isPending}>
          {mutation.isPending ? (
            <><span className={styles.spinner} /> Génération en cours…</>
          ) : "Générer la synthèse"}
        </button>
        {mutation.isPending && (
          <p className={styles.hint}>La synthèse peut prendre 30 à 60 secondes selon la durée de la vidéo.</p>
        )}
      </form>
    </div>
  );
}
