import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { searchSummaries } from "../api/summaries";
import { listThemes } from "../api/themes";
import SummaryCard from "../components/SummaryCard";
import SearchBar from "../components/SearchBar";
import ThemeSidebar from "../components/ThemeSidebar";
import styles from "./LibraryPage.module.css";

export default function LibraryPage() {
  const [q, setQ] = useState("");
  const [themeId, setThemeId] = useState<number | null>(null);

  const { data: themes = [] } = useQuery({ queryKey: ["themes"], queryFn: listThemes });
  const { data, isLoading } = useQuery({
    queryKey: ["summaries", q, themeId],
    queryFn: () => searchSummaries({ q, theme_id: themeId ?? undefined }),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <div className={styles.layout}>
      <ThemeSidebar themes={themes} selectedId={themeId} onSelect={setThemeId} />

      <section className={styles.content}>
        <div className={styles.header}>
          <h1 className={`${styles.title} u-lime-title`}>
            Bibliothèque
            {total > 0 && <span className={styles.count}>{total}</span>}
          </h1>
          <SearchBar value={q} onChange={setQ} />
        </div>

        {isLoading ? (
          <p className={styles.loading}>Chargement…</p>
        ) : items.length === 0 ? (
          <p className={styles.empty}>
            {q || themeId ? "Aucun résultat." : "Aucune synthèse — commencez par en créer une."}
          </p>
        ) : (
          <div className={styles.grid}>
            {items.map((s, i) => (
              <SummaryCard key={s.id} summary={s} index={i} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
