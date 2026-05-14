import { Link } from "react-router-dom";
import type { SummaryListItem } from "../api/summaries";
import styles from "./SummaryCard.module.css";

interface Props {
  summary: SummaryListItem;
}

export default function SummaryCard({ summary }: Props) {
  const thumb = `https://img.youtube.com/vi/${summary.youtube_id}/mqdefault.jpg`;
  const date = new Date(summary.created_at).toLocaleDateString("fr-FR", {
    day: "2-digit", month: "short", year: "numeric",
  });

  return (
    <Link to={`/library/${summary.id}`} className={styles.card}>
      <div className={styles.thumb}>
        <img src={thumb} alt={summary.title} loading="lazy" />
        <span className={styles.duration}>{summary.duration_read} min</span>
      </div>
      <div className={styles.body}>
        {summary.theme && (
          <span className={styles.theme} style={{ color: summary.theme.color }}>
            {summary.theme.icon && <span>{summary.theme.icon} </span>}
            {summary.theme.name}
          </span>
        )}
        <h3 className={styles.title}>{summary.title}</h3>
        <p className={styles.excerpt}>{summary.summary_short}</p>
        <div className={styles.footer}>
          <span className={styles.date}>{date}</span>
          {summary.tags.slice(0, 3).map((t) => (
            <span key={t} className={styles.tag}>{t}</span>
          ))}
        </div>
      </div>
    </Link>
  );
}
