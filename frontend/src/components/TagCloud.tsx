import { useQuery } from "@tanstack/react-query";
import { listTagCounts } from "../api/summaries";
import { tagColorIndex } from "../lib/tagColor";
import styles from "./TagCloud.module.css";

interface Props {
  selected: string | null;
  onSelect: (tag: string | null) => void;
}

const MIN_SIZE = 0.72;
const MAX_SIZE = 1.55;

export default function TagCloud({ selected, onSelect }: Props) {
  const { data: tags = [] } = useQuery({ queryKey: ["tag-cloud"], queryFn: listTagCounts });

  if (tags.length === 0) return null;

  const counts = tags.map((t) => t.count);
  const min = Math.min(...counts);
  const max = Math.max(...counts);

  const sizeFor = (count: number) => {
    if (max === min) return (MIN_SIZE + MAX_SIZE) / 2;
    const ratio = (count - min) / (max - min);
    return MIN_SIZE + ratio * (MAX_SIZE - MIN_SIZE);
  };

  return (
    <aside className={styles.sidebar}>
      <p className={styles.label}>Tags</p>
      <div className={styles.cloud}>
        {tags.map((t) => (
          <button
            key={t.name}
            type="button"
            className={`${styles.tag} ${styles[`tag${tagColorIndex(t.name)}`]} ${selected === t.name ? styles.active : ""}`}
            style={{ fontSize: `${sizeFor(t.count)}rem` }}
            aria-pressed={selected === t.name}
            title={`${t.count} vidéo${t.count !== 1 ? "s" : ""}`}
            onClick={() => onSelect(selected === t.name ? null : t.name)}
          >
            {t.name}
          </button>
        ))}
      </div>
    </aside>
  );
}
