import { useQuery } from "@tanstack/react-query";
import { getStats } from "../api/stats";
import styles from "./QuickStats.module.css";

function formatMinutes(min: number): string {
  if (min < 60) return `${min} min`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return m ? `${h}h ${m}min` : `${h}h`;
}

export default function QuickStats() {
  const { data } = useQuery({
    queryKey: ["stats"],
    queryFn: getStats,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  if (!data) return null;

  const items = [
    { icon: "▦", value: String(data.total_summaries), label: "Synthèses" },
    { icon: "◷", value: formatMinutes(data.total_read_minutes), label: "Temps de lecture économisé" },
    { icon: "#", value: String(data.total_tags), label: "Tags" },
  ];

  return (
    <div className={styles.row}>
      {items.map((it) => (
        <div key={it.label} className="u-glow-surface u-stat-card">
          <span className="u-stat-icon" aria-hidden="true">{it.icon}</span>
          <span className={styles.text}>
            <span className="u-stat-value">{it.value}</span>
            <span className="u-stat-label">{it.label}</span>
          </span>
        </div>
      ))}
    </div>
  );
}
