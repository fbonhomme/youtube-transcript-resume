import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getSummary, deleteSummary, updateSummary } from "../api/summaries";
import { listThemes } from "../api/themes";
import styles from "./SummaryDetailPage.module.css";

export default function SummaryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showTranscript, setShowTranscript] = useState(false);

  const { data: summary, isLoading } = useQuery({
    queryKey: ["summary", id],
    queryFn: () => getSummary(Number(id)),
    enabled: !!id,
  });

  const { data: themes = [] } = useQuery({ queryKey: ["themes"], queryFn: listThemes });

  const deleteMutation = useMutation({
    mutationFn: () => deleteSummary(Number(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["summaries"] });
      navigate("/library");
    },
  });

  const updateMutation = useMutation({
    mutationFn: (payload: { theme_id?: number | null }) => updateSummary(Number(id), payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["summary", id] }),
  });

  if (isLoading) return <p className={styles.loading}>Chargement…</p>;
  if (!summary) return <p className={styles.loading}>Synthèse introuvable.</p>;

  const thumb = `https://img.youtube.com/vi/${summary.youtube_id}/maxresdefault.jpg`;
  const date = new Date(summary.created_at).toLocaleDateString("fr-FR", {
    day: "2-digit", month: "long", year: "numeric",
  });

  return (
    <div className={styles.wrap}>
      <Link to="/library" className={styles.back}>← Bibliothèque</Link>

      <div className={styles.hero}>
        <a href={summary.youtube_url} target="_blank" rel="noreferrer" className={styles.thumbLink}>
          <img src={thumb} alt={summary.title} className={styles.thumb} />
          <span className={styles.playBtn}>▶</span>
        </a>
        <div className={styles.meta}>
          {summary.theme && (
            <span className={styles.theme} style={{ color: summary.theme.color }}>
              {summary.theme.icon} {summary.theme.name}
            </span>
          )}
          <h1 className={styles.title}>{summary.title}</h1>
          <p className={styles.subtitle}>{summary.summary_short}</p>
          <div className={styles.pills}>
            <span className={styles.pill}>{summary.duration_read} min de lecture</span>
            <span className={styles.pill}>{summary.language.toUpperCase()}</span>
            {summary.tags.map((t) => <span key={t} className={styles.tag}>{t}</span>)}
          </div>
          <p className={styles.date}>{date}</p>
        </div>
      </div>

      {summary.key_points.length > 0 && (
        <section className={styles.section}>
          <h2>Points clés</h2>
          <ul className={styles.keyPoints}>
            {summary.key_points.map((p, i) => (
              <li key={i}>{p}</li>
            ))}
          </ul>
        </section>
      )}

      <section className={styles.section}>
        <h2>Résumé détaillé</h2>
        <p className={styles.longText}>{summary.summary_long}</p>
      </section>

      {summary.sections.length > 0 && (
        <section className={styles.section}>
          <h2>Sections</h2>
          {summary.sections.map((s, i) => (
            <div key={i} className={styles.sectionBlock}>
              <h3 className={styles.sectionTitle}>{s.title}</h3>
              <p>{s.content}</p>
            </div>
          ))}
        </section>
      )}

      <section className={`${styles.section} ${styles.noPrint}`}>
        <h2>Modifier</h2>
        <label className={styles.field}>
          <span>Thème</span>
          <select
            name="theme"
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
        </label>
      </section>

      <section className={`${styles.section} ${styles.noPrint}`}>
        <button className={styles.transcriptToggle} onClick={() => setShowTranscript((v) => !v)}>
          {showTranscript ? "Masquer" : "Afficher"} le transcript original
        </button>
        {showTranscript && (
          <pre className={styles.transcript}>{summary.transcript}</pre>
        )}
      </section>

      <div className={styles.actions}>
        <a href={summary.youtube_url} target="_blank" rel="noreferrer" className={styles.btnOutline}>
          Voir sur YouTube ↗
        </a>
        <button className={styles.btnOutline} onClick={() => window.print()}>
          Exporter en PDF
        </button>
        <button
          className={styles.btnDanger}
          onClick={() => { if (confirm("Supprimer cette synthèse ?")) deleteMutation.mutate(); }}
          disabled={deleteMutation.isPending}
        >
          Supprimer
        </button>
      </div>
    </div>
  );
}
