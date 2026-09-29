import { Link } from "react-router-dom";
import type { SummaryListItem } from "../api/summaries";
import type { Theme } from "../api/themes";
import { tagColorIndex } from "../lib/tagColor";
import styles from "./SummaryCard.module.css";

interface Props {
  summary: SummaryListItem;
  index?: number;
  // Thème suggéré par Jev, à valider (synthèse sans thème).
  suggestedTheme?: Theme;
  onAcceptSuggestion?: () => void;
  onIgnoreSuggestion?: () => void;
  busy?: boolean;
}

export default function SummaryCard({
  summary,
  index = 0,
  suggestedTheme,
  onAcceptSuggestion,
  onIgnoreSuggestion,
  busy = false,
}: Props) {
  const thumb = `https://img.youtube.com/vi/${summary.youtube_id}/mqdefault.jpg`;
  const thumbFallback = `https://img.youtube.com/vi/${summary.youtube_id}/hqdefault.jpg`;
  const date = new Date(summary.created_at).toLocaleDateString("fr-FR", {
    day: "2-digit", month: "short", year: "numeric",
  });
  const pending = !summary.theme && suggestedTheme !== undefined;
  const confidence = summary.theme_confidence != null ? Math.round(summary.theme_confidence * 100) : null;

  return (
    <article
      className={`${styles.card} ${pending ? styles.pending : ""}`}
      style={{ animationDelay: `${index * 60}ms` }}
    >
      <Link to={`/library/${summary.id}`} className={styles.link}>
        <div className={styles.thumb}>
          <img
            src={thumb}
            alt={summary.title}
            loading="lazy"
            onError={(e) => { (e.target as HTMLImageElement).src = thumbFallback; }}
          />
          <div className={styles.overlay} />
          {pending && <span className={styles.pendingRibbon}>À valider</span>}
          <span className={styles.duration}>{summary.duration_read} min</span>
        </div>

        <div className={styles.body}>
          {summary.theme ? (
            <span className={styles.theme} style={{ color: summary.theme.color }}>
              <span className={styles.themeDot} style={{ background: summary.theme.color }} />
              {summary.theme.icon && `${summary.theme.icon} `}{summary.theme.name}
            </span>
          ) : !pending && (
            <span className={`${styles.theme} ${styles.noTheme}`}>Sans thème</span>
          )}
          <h3 className={styles.title}>{summary.title}</h3>
          <p className={styles.excerpt}>{summary.summary_short}</p>
          <div className={styles.footer}>
            <span className={styles.date}>{date}</span>
            {summary.tags.slice(0, 2).map((t) => (
              <span key={t} className={`${styles.tag} ${styles[`tag${tagColorIndex(t)}`]}`}>{t}</span>
            ))}
          </div>
        </div>
      </Link>

      {pending && (
        <div className={styles.suggestion}>
          <span className={styles.suggestionLabel}>
            Thème suggéré :{" "}
            <strong style={{ color: suggestedTheme.color }}>
              {suggestedTheme.icon ? `${suggestedTheme.icon} ` : ""}{suggestedTheme.name}
            </strong>
            {confidence != null && <span className={styles.confidence}> {confidence} %</span>}
          </span>
          <div className={styles.suggestionActions}>
            <button
              type="button"
              className={styles.accept}
              onClick={onAcceptSuggestion}
              disabled={busy}
              aria-label={`Accepter le thème ${suggestedTheme.name} pour « ${summary.title} »`}
            >
              ✓ Accepter
            </button>
            <button
              type="button"
              className={styles.ignore}
              onClick={onIgnoreSuggestion}
              disabled={busy}
              aria-label={`Ignorer la suggestion pour « ${summary.title} »`}
            >
              ✗ Ignorer
            </button>
          </div>
        </div>
      )}
    </article>
  );
}
