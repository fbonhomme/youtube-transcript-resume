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
      <button
        className={`${styles.item} ${selectedId === null ? styles.active : ""}`}
        onClick={() => onSelect(null)}
      >
        <span className={styles.dot} style={{ background: "var(--muted)" }} />
        Tous
      </button>
      {themes.map((t) => (
        <button
          key={t.id}
          className={`${styles.item} ${selectedId === t.id ? styles.active : ""}`}
          onClick={() => onSelect(t.id)}
        >
          <span className={styles.dot} style={{ background: t.color }} />
          {t.icon && <span>{t.icon} </span>}
          <span className={styles.name}>{t.name}</span>
          <span className={styles.count}>{t.summary_count}</span>
        </button>
      ))}
    </aside>
  );
}
