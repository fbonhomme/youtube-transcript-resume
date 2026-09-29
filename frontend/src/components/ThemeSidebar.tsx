import type { Theme } from "../api/themes";
import type { ThemeStatus } from "../api/summaries";
import styles from "./ThemeSidebar.module.css";

interface Props {
  themes: Theme[];
  selectedId: number | null;
  onSelect: (id: number | null) => void;
  status: ThemeStatus | null;
  onStatus: (status: ThemeStatus) => void;
  counts?: Record<ThemeStatus, number>;
}

const STATUS_FILTERS: { value: ThemeStatus; label: string; className: string }[] = [
  { value: "pending", label: "À valider", className: styles.pendingDot },
  { value: "unthemed", label: "Sans thème", className: styles.unthemedDot },
];

export default function ThemeSidebar({ themes, selectedId, onSelect, status, onStatus, counts }: Props) {
  return (
    <aside className={styles.sidebar}>
      <p className={styles.label}>Thèmes</p>
      <div className={styles.list}>
        <button
          className={`u-pill-filter ${selectedId === null && status === null ? "is-active" : ""}`}
          aria-pressed={selectedId === null && status === null}
          onClick={() => onSelect(null)}
        >
          Tous
        </button>
        {STATUS_FILTERS.map((f) => {
          const count = counts?.[f.value] ?? 0;
          // Un filtre vide n'est affiché que s'il est sélectionné (pour pouvoir en sortir).
          if (count === 0 && status !== f.value) return null;
          return (
            <button
              key={f.value}
              className={`u-pill-filter ${status === f.value ? "is-active" : ""}`}
              aria-pressed={status === f.value}
              onClick={() => onStatus(f.value)}
            >
              <span className={`${styles.dot} ${f.className}`} aria-hidden="true" />
              <span className={styles.name}>{f.label}</span>
              <span className={styles.count}>{count}</span>
            </button>
          );
        })}
        <hr className={styles.separator} />
        {themes.map((t) => (
          <button
            key={t.id}
            className={`u-pill-filter ${selectedId === t.id ? "is-active" : ""}`}
            aria-pressed={selectedId === t.id}
            onClick={() => onSelect(t.id)}
          >
            <span
              className={styles.dot}
              style={{ background: t.color }}
              aria-hidden="true"
            />
            {t.icon ? `${t.icon} ` : ""}
            <span className={styles.name}>{t.name}</span>
            <span className={styles.count}>{t.summary_count}</span>
          </button>
        ))}
      </div>
    </aside>
  );
}
