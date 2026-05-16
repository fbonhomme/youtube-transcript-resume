import type { Theme } from "../api/themes";
import styles from "./ThemeSidebar.module.css";

interface Props {
  themes: Theme[];
  selectedId: number | null;
  onSelect: (id: number | null) => void;
}

export default function ThemeSidebar({ themes, selectedId, onSelect }: Props) {
  return (
    <aside className={styles.sidebar}>
      <p className={styles.label}>Thèmes</p>
      <div className={styles.list}>
        <button
          className={`u-pill-filter ${selectedId === null ? "is-active" : ""}`}
          aria-pressed={selectedId === null}
          onClick={() => onSelect(null)}
        >
          Tous
        </button>
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
