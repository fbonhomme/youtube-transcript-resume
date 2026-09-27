import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { analyzeSummary, getSummary, deleteSummary, updateSummary } from "../api/summaries";
import type { ScoreKey } from "../api/summaries";
import { listThemes } from "../api/themes";
import { listModels } from "../api/models";
import { useConfirm } from "../components/ConfirmDialog";
import { SCORE_LABELS, levelLabel } from "../lib/scores";
import styles from "./SummaryDetailPage.module.css";

export default function SummaryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const confirm = useConfirm();
  const [showTranscript, setShowTranscript] = useState(false);

  const { data: summary, isLoading } = useQuery({
    queryKey: ["summary", id],
    queryFn: () => getSummary(Number(id)),
    enabled: !!id,
  });

  const { data: themes = [] } = useQuery({ queryKey: ["themes"], queryFn: listThemes });
  const { data: models = [] } = useQuery({ queryKey: ["models"], queryFn: listModels });

  const deleteMutation = useMutation({
    mutationFn: () => deleteSummary(Number(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["summaries"] });
      navigate("/library");
    },
  });

  const updateMutation = useMutation({
    mutationFn: (payload: { theme_id?: number | null; feedback?: number | null; theme_suggestion_id?: null }) =>
      updateSummary(Number(id), payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["summary", id] }),
  });

  const analyzeMutation = useMutation({
    mutationFn: () => analyzeSummary(Number(id)),
    onSuccess: (data) => {
      queryClient.setQueryData(["summary", id], data);
      queryClient.invalidateQueries({ queryKey: ["summaries"] });
    },
  });

  if (isLoading) return <p className={styles.loading}>Chargement…</p>;
  if (!summary) return <p className={styles.loading}>Synthèse introuvable.</p>;

  const date = new Date(summary.created_at).toLocaleDateString("fr-FR", {
    day: "2-digit", month: "long", year: "numeric",
  });

  const scrollToSection = (i: number) => {
    document.getElementById(`section-${i}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const suggestedTheme = themes.find((t) => t.id === summary.theme_suggestion_id);
  const confidencePct = summary.theme_confidence != null ? Math.round(summary.theme_confidence * 100) : null;
  const analyzeError = analyzeMutation.isError
    ? (analyzeMutation.error as { response?: { status?: number } }).response?.status === 503
      ? "Jev n'est pas configuré (OPENROUTER_API_KEY)."
      : "L'analyse Jev a échoué."
    : "";

  const setFeedback = (value: number) => {
    updateMutation.mutate({ feedback: summary.feedback === value ? null : value });
  };

  return (
    <div className={styles.wrap}>
      <Link to="/library" className={styles.back}>← Bibliothèque</Link>

      <div className="u-split">
        <div className={styles.left}>
          <div className={styles.player}>
            <iframe
              src={`https://www.youtube.com/embed/${summary.youtube_id}`}
              title={summary.title}
              loading="lazy"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>
          {summary.theme && (
            <span className={styles.theme} style={{ color: summary.theme.color }}>
              {summary.theme.icon} {summary.theme.name}
            </span>
          )}
          <h1 className={`${styles.title} u-lime-title`}>{summary.title}</h1>
          <p className={styles.subtitle}>{summary.summary_short}</p>
          <div className={styles.pills}>
            <span className={styles.pill}>{summary.duration_read} min de lecture</span>
            <span className={styles.pill}>{summary.language.toUpperCase()}</span>
            {summary.model && (
              <span className={styles.pill}>
                {models.find((m) => m.id === summary.model)?.label ?? summary.model}
              </span>
            )}
            {summary.tags.map((t) => <span key={t} className={styles.tag}>{t}</span>)}
          </div>
          <p className={styles.date}>{date}</p>

          <div className={styles.actions}>
            <button
              className={`${styles.feedbackBtn} ${summary.feedback === 1 ? styles.liked : ""}`}
              onClick={() => setFeedback(1)}
              disabled={updateMutation.isPending}
              aria-label="J'aime"
              aria-pressed={summary.feedback === 1}
            >
              👍
            </button>
            <button
              className={`${styles.feedbackBtn} ${summary.feedback === -1 ? styles.disliked : ""}`}
              onClick={() => setFeedback(-1)}
              disabled={updateMutation.isPending}
              aria-label="Je n'aime pas"
              aria-pressed={summary.feedback === -1}
            >
              👎
            </button>
            <a href={summary.youtube_url} target="_blank" rel="noreferrer" className={styles.btnOutline}>
              Voir sur YouTube ↗
            </a>
            <button className={styles.btnOutline} onClick={() => window.print()}>
              Exporter en PDF
            </button>
          </div>

          <div className={styles.field}>
            <span className={styles.fieldLabel}>Thème</span>
            <select
              className={styles.select}
              value={summary.theme_id ?? ""}
              onChange={(e) =>
                updateMutation.mutate({ theme_id: e.target.value ? Number(e.target.value) : null })
              }
            >
              <option value="">— Aucun —</option>
              {themes.map((t) => (
                <option key={t.id} value={t.id}>{t.icon ? `${t.icon} ` : ""}{t.name}</option>
              ))}
            </select>
            {summary.theme && confidencePct != null && (
              <span className={styles.jevNote}>Classé automatiquement par Jev ({confidencePct} %)</span>
            )}
          </div>

          {suggestedTheme && !summary.theme_id && (
            <div className={styles.suggestion}>
              <span>
                Jev suggère <strong>{suggestedTheme.icon ? `${suggestedTheme.icon} ` : ""}{suggestedTheme.name}</strong>
                {confidencePct != null && ` (${confidencePct} %)`}
              </span>
              <div className={styles.suggestionActions}>
                <button
                  className={styles.btnOutline}
                  onClick={() => updateMutation.mutate({ theme_id: suggestedTheme.id })}
                  disabled={updateMutation.isPending}
                >
                  Accepter
                </button>
                <button
                  className={styles.btnGhost}
                  onClick={() => updateMutation.mutate({ theme_suggestion_id: null })}
                  disabled={updateMutation.isPending}
                >
                  Ignorer
                </button>
              </div>
            </div>
          )}

          <section className={styles.scores}>
            <span className={styles.fieldLabel}>Analyse Jev</span>
            {summary.scores ? (
              <ul className={styles.scoreList}>
                {(Object.keys(SCORE_LABELS) as ScoreKey[]).map((key) => {
                  const value = summary.scores?.[key];
                  if (value == null) return null;
                  return (
                    <li key={key} className={styles.scoreRow}>
                      <span className={styles.scoreName}>{SCORE_LABELS[key].label}</span>
                      <span className={styles.scoreBar}>
                        <span style={{ width: `${(value / 3) * 100}%` }} />
                      </span>
                      <span className={styles.scoreLevel}>{levelLabel(key, value)}</span>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className={styles.jevNote}>Pas encore analysée.</p>
            )}
            <button
              className={styles.btnOutline}
              onClick={() => analyzeMutation.mutate()}
              disabled={analyzeMutation.isPending}
            >
              {analyzeMutation.isPending ? "Analyse…" : summary.scores ? "Ré-analyser" : "Analyser avec Jev"}
            </button>
            {analyzeError && <p className={styles.jevError}>{analyzeError}</p>}
          </section>

          <button
            className={styles.btnDanger}
            onClick={async () => {
              if (await confirm("Supprimer cette synthèse ?", { confirmLabel: "Supprimer", danger: true })) {
                deleteMutation.mutate();
              }
            }}
            disabled={deleteMutation.isPending}
          >
            Supprimer
          </button>
        </div>

        <div className={styles.right}>
          {summary.key_points.length > 0 && (
            <section className={styles.takeaways}>
              <h2>Key Takeaways</h2>
              <ul>
                {summary.key_points.map((p, i) => <li key={i}>{p}</li>)}
              </ul>
            </section>
          )}

          {summary.sections.length > 0 && (
            <section className={styles.toc}>
              <h2>Sommaire</h2>
              <ol>
                {summary.sections.map((s, i) => (
                  <li key={i}>
                    <button className={styles.tocLink} onClick={() => scrollToSection(i)}>
                      {s.title}
                    </button>
                  </li>
                ))}
              </ol>
            </section>
          )}

          <section className={styles.section}>
            <h2>Résumé détaillé</h2>
            <p className={styles.longText}>{summary.summary_long}</p>
          </section>

          {summary.sections.map((s, i) => (
            <section key={i} id={`section-${i}`} className={styles.section}>
              <h3 className={styles.sectionTitle}>{s.title}</h3>
              <p>{s.content}</p>
            </section>
          ))}

          <section className={`${styles.section} ${styles.noPrint}`}>
            <button className={styles.transcriptToggle} onClick={() => setShowTranscript((v) => !v)}>
              {showTranscript ? "Masquer" : "Afficher"} le transcript original
            </button>
            {showTranscript && (
              summary.transcript
                ? <pre className={styles.transcript}>{summary.transcript}</pre>
                : <p className={styles.noTranscript}>Transcript non disponible pour cette synthèse.</p>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
