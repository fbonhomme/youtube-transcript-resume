import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createSummary,
  exportSummariesUrl,
  importPreview,
  type ImportPreviewItem,
} from "../api/summaries";
import { listThemes } from "../api/themes";
import styles from "./ImportPage.module.css";

type GenStatus = "idle" | "pending" | "done" | "error";

export default function ImportPage() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [items, setItems] = useState<ImportPreviewItem[] | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [themeId, setThemeId] = useState<number | null>(null);
  const [tagInput, setTagInput] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [genStatus, setGenStatus] = useState<Record<string, { status: GenStatus; message?: string }>>({});
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const stopRef = useRef(false);

  const { data: themes = [] } = useQuery({ queryKey: ["themes"], queryFn: listThemes });

  const previewMutation = useMutation({
    mutationFn: importPreview,
    onSuccess: (result) => {
      setItems(result.items);
      setGenStatus({});
      setSelected(new Set(
        result.items.filter((it) => !it.error && !it.already_imported).map((it) => it.video_id),
      ));
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) previewMutation.mutate(file);
  };

  const toggleSelected = (videoId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(videoId)) next.delete(videoId); else next.add(videoId);
      return next;
    });
  };

  const addTag = () => {
    const t = tagInput.trim();
    if (t && !tags.includes(t)) setTags([...tags, t]);
    setTagInput("");
  };

  const selectableItems = (items ?? []).filter((it) => !it.error);
  const selectedCount = selectableItems.filter((it) => selected.has(it.video_id)).length;

  const runGeneration = async () => {
    const toRun = selectableItems.filter((it) => selected.has(it.video_id));
    if (toRun.length === 0) return;
    stopRef.current = false;
    setGenerating(true);
    setProgress({ done: 0, total: toRun.length });

    for (const it of toRun) {
      if (stopRef.current) break;
      setGenStatus((s) => ({ ...s, [it.video_id]: { status: "pending" } }));
      try {
        await createSummary({ url: it.url, theme_id: themeId, tags });
        setGenStatus((s) => ({ ...s, [it.video_id]: { status: "done" } }));
      } catch (err: unknown) {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
          ?? "Erreur inconnue";
        setGenStatus((s) => ({ ...s, [it.video_id]: { status: "error", message: msg } }));
      }
      setProgress((p) => ({ ...p, done: p.done + 1 }));
    }

    setGenerating(false);
    queryClient.invalidateQueries({ queryKey: ["summaries"] });
  };

  const badge = (it: ImportPreviewItem) => {
    if (it.error) return <span className={`${styles.badge} ${styles.badgeError}`}>Erreur</span>;
    if (it.already_imported) return <span className={`${styles.badge} ${styles.badgeExisting}`}>Déjà en base</span>;
    return <span className={`${styles.badge} ${styles.badgeNew}`}>Nouvelle</span>;
  };

  const statusIcon = (videoId: string) => {
    const s = genStatus[videoId]?.status;
    if (s === "pending") return <span className={styles.spinnerSmall} />;
    if (s === "done") return <span className={styles.ok}>✓</span>;
    if (s === "error") return <span className={styles.ko} title={genStatus[videoId]?.message}>✗</span>;
    return null;
  };

  return (
    <div className={styles.wrap}>
      <div className={styles.heading}>
        <h1 className={`${styles.title} u-lime-title`}>Importer des vidéos</h1>
        <p className={styles.subtitle}>
          Charge un fichier texte (une URL YouTube par ligne) pour générer plusieurs synthèses d'un coup.
        </p>
      </div>

      <div className={`${styles.card} u-glow-surface`}>
        <div className={styles.fileRow}>
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt"
            onChange={handleFileChange}
            className={styles.fileInput}
            disabled={previewMutation.isPending || generating}
          />
          <a
            className={styles.exportLink}
            href={exportSummariesUrl()}
            download
          >
            Exporter la liste actuelle (.txt)
          </a>
        </div>
        {previewMutation.isPending && <p className={styles.hint}>Analyse du fichier…</p>}
        {previewMutation.isError && <p className={styles.error}>Impossible d'analyser ce fichier.</p>}
      </div>

      {items && items.length > 0 && (
        <>
          <div className={`${styles.card} u-glow-surface`}>
            <div className={styles.row}>
              <div className={styles.field}>
                <span className={styles.fieldLabel}>Thème</span>
                <select
                  value={themeId ?? ""}
                  onChange={(e) => setThemeId(e.target.value ? Number(e.target.value) : null)}
                  className={styles.select}
                  disabled={generating}
                >
                  <option value="">— Aucun —</option>
                  {themes.map((t) => (
                    <option key={t.id} value={t.id}>{t.icon ? `${t.icon} ` : ""}{t.name}</option>
                  ))}
                </select>
              </div>

              <div className={styles.field}>
                <span className={styles.fieldLabel}>Tags (appliqués à tout le lot)</span>
                <div className={styles.tagRow}>
                  <input
                    type="text"
                    placeholder="Ajouter un tag…"
                    value={tagInput}
                    onChange={(e) => setTagInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTag(); } }}
                    className={styles.tagInput}
                    disabled={generating}
                  />
                  <button type="button" className={styles.addBtn} onClick={addTag} disabled={generating}>+</button>
                </div>
                {tags.length > 0 && (
                  <div className={styles.tags}>
                    {tags.map((t) => (
                      <span key={t} className={styles.tag}>
                        {t}
                        <button type="button" onClick={() => setTags(tags.filter((x) => x !== t))}>×</button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className={`${styles.card} u-glow-surface`}>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th></th>
                    <th>Titre</th>
                    <th>Statut</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((it) => (
                    <tr key={it.url}>
                      <td>
                        {!it.error && (
                          <input
                            type="checkbox"
                            checked={selected.has(it.video_id)}
                            onChange={() => toggleSelected(it.video_id)}
                            disabled={generating}
                          />
                        )}
                      </td>
                      <td className={styles.titleCell}>
                        <span className={styles.videoTitle}>{it.title || it.url}</span>
                        <span className={styles.videoUrl}>{it.url}</span>
                      </td>
                      <td>{badge(it)}</td>
                      <td className={styles.statusCell}>{statusIcon(it.video_id)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <button
              type="button"
              className={`${styles.submit} u-pill-btn`}
              onClick={runGeneration}
              disabled={generating || selectedCount === 0}
            >
              {generating
                ? <><span className={styles.spinner} /> Génération {progress.done}/{progress.total}…</>
                : `Générer les synthèses sélectionnées (${selectedCount})`}
            </button>

            {generating && (
              <p className={styles.hint}>
                Chaque synthèse prend 30 à 60 secondes — le lot se génère vidéo par vidéo.
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
