import { Link } from "react-router-dom";
import type { SummaryListItem } from "../api/summaries";
import styles from "./SummaryCard.module.css";

interface Props {
  summary: SummaryListItem;
  index?: number;
}

function tagColorIndex(tag: string): number {
  let hash = 0;
  for (let i = 0; i < tag.length; i++) {
    hash = (hash * 31 + tag.charCodeAt(i)) | 0;
  }
  return Math.abs(hash) % 4;
}

export default function SummaryCard({ summary, index = 0 }: Props) {
  const thumb = `https://img.youtube.com/vi/${summary.youtube_id}/mqdefault.jpg`;
  const thumbFallback = `https://img.youtube.com/vi/${summary.youtube_id}/hqdefault.jpg`;
  const date = new Date(summary.created_at).toLocaleDateString("fr-FR", {
    day: "2-digit", month: "short", year: "numeric",
  });

  return (
    <Link
      to={`/library/${summary.id}`}
      className={styles.card}
      style={{ animationDelay: `${index * 60}ms` }}
    >
      <div className={styles.thumb}>
        <img
          src={thumb}
          alt={summary.title}
          loading="lazy"
          onError={(e) => { (e.target as HTMLImageElement).src = thumbFallback; }}
        />
        <div className={styles.overlay} />
        <span className={styles.duration}>{summary.duration_read} min</span>
      </div>

      <div className={styles.body}>
        {summary.theme && (
          <span className={styles.theme} style={{ color: summary.theme.color }}>
            <span className={styles.themeDot} style={{ background: summary.theme.color }} />
            {summary.theme.icon && `${summary.theme.icon} `}{summary.theme.name}
          </span>
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
  );
}
