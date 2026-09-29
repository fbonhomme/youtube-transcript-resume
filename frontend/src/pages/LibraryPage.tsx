import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { acceptAllSuggestions, getThemeStatus, searchSummaries, updateSummary } from "../api/summaries";
import type { SortKey, ThemeStatus } from "../api/summaries";
import { SORT_OPTIONS } from "../lib/scores";
import { listThemes } from "../api/themes";
import SummaryCard from "../components/SummaryCard";
import SearchBar from "../components/SearchBar";
import QuickStats from "../components/QuickStats";
import ThemeSidebar from "../components/ThemeSidebar";
import TagCloud from "../components/TagCloud";
import { useConfirm } from "../components/ConfirmDialog";
import styles from "./LibraryPage.module.css";

export default function LibraryPage() {
  const queryClient = useQueryClient();
  const confirm = useConfirm();
  const [q, setQ] = useState("");
  const [themeId, setThemeId] = useState<number | null>(null);
  const [status, setStatus] = useState<ThemeStatus | null>(null);
  const [tag, setTag] = useState<string | null>(null);
  const [sort, setSort] = useState<SortKey>("recent");

  const { data: themes = [] } = useQuery({ queryKey: ["themes"], queryFn: listThemes });
  const { data: themeStatus } = useQuery({ queryKey: ["theme-status"], queryFn: getThemeStatus });
  const { data, isLoading } = useQuery({
    queryKey: ["summaries", q, themeId, status, tag, sort],
    queryFn: () => searchSummaries({
      q,
      theme_id: themeId ?? undefined,
      status: status ?? undefined,
      tag: tag ?? undefined,
      sort,
    }),
  });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["summaries"] });
    queryClient.invalidateQueries({ queryKey: ["themes"] });
    queryClient.invalidateQueries({ queryKey: ["theme-status"] });
    queryClient.invalidateQueries({ queryKey: ["summary"] });
  };

  const decideMutation = useMutation({
    mutationFn: ({ id, themeIdToApply }: { id: number; themeIdToApply: number | null }) =>
      themeIdToApply !== null
        ? updateSummary(id, { theme_id: themeIdToApply })
        : updateSummary(id, { theme_suggestion_id: null }),
    onSuccess: refresh,
  });

  const acceptAllMutation = useMutation({ mutationFn: acceptAllSuggestions, onSuccess: refresh });

  const selectTheme = (id: number | null) => { setThemeId(id); setStatus(null); };
  const selectStatus = (s: ThemeStatus) => { setStatus(s); setThemeId(null); };

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pendingCount = themeStatus?.pending ?? 0;
  const themeById = new Map(themes.map((t) => [t.id, t]));

  return (
    <div className={styles.layout}>
      <ThemeSidebar
        themes={themes}
        selectedId={themeId}
        onSelect={selectTheme}
        status={status}
        onStatus={selectStatus}
        counts={themeStatus}
      />

      <section className={styles.content}>
        <QuickStats />

        {pendingCount > 0 && (
          <div className={styles.banner} role="status">
            <span>
              🔔 <strong>{pendingCount}</strong>{" "}
              {pendingCount > 1
                ? "synthèses attendent la validation de leur thème"
                : "synthèse attend la validation de son thème"}
            </span>
            <div className={styles.bannerActions}>
              {status !== "pending" && (
                <button type="button" className={styles.bannerBtn} onClick={() => selectStatus("pending")}>
                  Voir
                </button>
              )}
              <button
                type="button"
                className={`${styles.bannerBtn} ${styles.bannerPrimary}`}
                disabled={acceptAllMutation.isPending}
                onClick={async () => {
                  const ok = await confirm(
                    `Appliquer le thème suggéré par Jev aux ${pendingCount} synthèse${pendingCount > 1 ? "s" : ""} en attente ?`,
                    { confirmLabel: "Tout accepter" },
                  );
                  if (ok) acceptAllMutation.mutate();
                }}
              >
                Tout accepter
              </button>
            </div>
          </div>
        )}

        <div className={styles.header}>
          <h1 className={`${styles.title} u-lime-title`}>
            Bibliothèque
            {total > 0 && <span className={styles.count}>{total}</span>}
          </h1>
          <SearchBar value={q} onChange={setQ} />
          <select
            className={styles.sort}
            value={sort}
            onChange={(e) => setSort(e.target.value as SortKey)}
            aria-label="Trier par"
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <p className={styles.empty}>Chargement…</p>
        ) : items.length === 0 ? (
          <p className={styles.empty}>
            {status === "pending"
              ? "Aucune suggestion à valider."
              : q || themeId || status || tag
                ? "Aucun résultat."
                : "Aucune synthèse — commencez par en créer une."}
          </p>
        ) : (
          <div className={styles.grid}>
            {items.map((s, i) => {
              const suggested = !s.theme && s.theme_suggestion_id != null
                ? themeById.get(s.theme_suggestion_id)
                : undefined;
              return (
                <SummaryCard
                  key={s.id}
                  summary={s}
                  index={i}
                  suggestedTheme={suggested}
                  busy={decideMutation.isPending && decideMutation.variables?.id === s.id}
                  onAcceptSuggestion={() => suggested && decideMutation.mutate({ id: s.id, themeIdToApply: suggested.id })}
                  onIgnoreSuggestion={() => decideMutation.mutate({ id: s.id, themeIdToApply: null })}
                />
              );
            })}
          </div>
        )}
      </section>

      <TagCloud selected={tag} onSelect={setTag} />
    </div>
  );
}
