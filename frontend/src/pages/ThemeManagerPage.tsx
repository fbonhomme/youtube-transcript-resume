import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listThemes, createTheme, updateTheme, deleteTheme } from "../api/themes";
import type { Theme } from "../api/themes";
import { analyzeLibrary } from "../api/summaries";
import type { AnalyzeReport } from "../api/summaries";
import { useConfirm } from "../components/ConfirmDialog";
import styles from "./ThemeManagerPage.module.css";

type ThemeFormData = { name: string; color: string; icon: string | null; description: string | null };

const COLORS = ["#6366f1","#f43f5e","#10b981","#f59e0b","#3b82f6","#8b5cf6","#ec4899","#14b8a6"];

function ThemeForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: Partial<Theme>;
  onSave: (data: ThemeFormData) => void;
  onCancel?: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [color, setColor] = useState(initial?.color ?? COLORS[0]);
  const [icon, setIcon] = useState(initial?.icon ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");

  return (
    <form
      className={styles.form}
      onSubmit={(e) => { e.preventDefault(); onSave({ name, color, icon: icon || null, description: description.trim() || null }); }}
    >
      <input
        name="theme-name"
        className={styles.input}
        placeholder="Nom du thème"
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
      />
      <input
        name="theme-icon"
        className={styles.input}
        placeholder="Emoji (optionnel)"
        value={icon}
        onChange={(e) => setIcon(e.target.value)}
        style={{ maxWidth: 80 }}
      />
      <input
        name="theme-description"
        className={`${styles.input} ${styles.fullWidth}`}
        placeholder="Description pour le classement auto (ex. : outils de dev, IA, cloud)"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <div className={styles.colors}>
        {COLORS.map((c) => (
          <button
            type="button"
            key={c}
            className={`${styles.colorDot} ${color === c ? styles.selectedColor : ""}`}
            style={{ background: c }}
            onClick={() => setColor(c)}
          />
        ))}
      </div>
      <div className={styles.formActions}>
        <button type="submit" className={`${styles.btnPrimary} u-pill-btn`}>
          {initial?.id ? "Enregistrer" : "Créer"}
        </button>
        {onCancel && (
          <button type="button" className={styles.btnGhost} onClick={onCancel}>Annuler</button>
        )}
      </div>
    </form>
  );
}

export default function ThemeManagerPage() {
  const queryClient = useQueryClient();
  const confirm = useConfirm();
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [report, setReport] = useState<AnalyzeReport | null>(null);

  const { data: themes = [] } = useQuery({ queryKey: ["themes"], queryFn: listThemes });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["themes"] });

  const createMutation = useMutation({
    mutationFn: createTheme,
    onSuccess: invalidate,
    onError: () => setError("Nom déjà utilisé ou erreur serveur."),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, ...payload }: { id: number } & ThemeFormData) =>
      updateTheme(id, payload),
    onSuccess: () => { invalidate(); setEditingId(null); },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteTheme,
    onSuccess: invalidate,
  });

  const analyzeMutation = useMutation({
    mutationFn: analyzeLibrary,
    onMutate: () => setReport(null),
    onSuccess: (data) => {
      setReport(data);
      invalidate();
      queryClient.invalidateQueries({ queryKey: ["summaries"] });
      queryClient.invalidateQueries({ queryKey: ["summary"] });
    },
  });

  return (
    <div className={styles.wrap}>
      <h1 className={`${styles.title} u-lime-title`}>Gestion des thèmes</h1>

      <section className={`${styles.card} u-glow-surface`}>
        <h2>Nouveau thème</h2>
        {error && <p className={styles.error}>{error}</p>}
        <ThemeForm
          onSave={(data) => { setError(""); createMutation.mutate(data); }}
        />
      </section>

      <section className={`${styles.card} u-glow-surface`}>
        <h2>Thèmes existants</h2>
        {themes.length === 0 ? (
          <p className={styles.empty}>Aucun thème créé.</p>
        ) : (
          <ul className={styles.list}>
            {themes.map((t) => (
              <li key={t.id} className={styles.item}>
                {editingId === t.id ? (
                  <ThemeForm
                    initial={t}
                    onSave={(data) => updateMutation.mutate({ id: t.id, ...data })}
                    onCancel={() => setEditingId(null)}
                  />
                ) : (
                  <div className={styles.row}>
                    <span className={styles.dot} style={{ background: t.color }} />
                    <span className={styles.themeName}>
                      {t.icon && <span>{t.icon} </span>}
                      {t.name}
                      {t.description && <span className={styles.description}>{t.description}</span>}
                    </span>
                    <span className={styles.count}>{t.summary_count} synthèse{t.summary_count !== 1 ? "s" : ""}</span>
                    <div className={styles.rowActions}>
                      <button className={styles.btnGhost} onClick={() => setEditingId(t.id)}>Modifier</button>
                      <button
                        className={styles.btnGhostDanger}
                        onClick={async () => {
                          const count = t.summary_count;
                          const message = count > 0
                            ? `Supprimer "${t.name}" ? ${count} synthèse${count !== 1 ? "s" : ""} ${count !== 1 ? "seront détachées" : "sera détachée"}.`
                            : `Supprimer "${t.name}" ?`;
                          if (await confirm(message, { confirmLabel: "Supprimer", danger: true })) {
                            deleteMutation.mutate(t.id);
                          }
                        }}
                      >
                        Supprimer
                      </button>
                    </div>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className={`${styles.card} u-glow-surface`}>
        <h2>Classement automatique (Jev)</h2>
        <p className={styles.hint}>
          Note toutes les synthèses et range celles qui n'ont pas de thème. Un thème déjà
          choisi n'est jamais modifié ; en cas de doute, Jev propose une suggestion à valider.
        </p>
        <div className={styles.formActions}>
          <button
            className={`${styles.btnPrimary} u-pill-btn`}
            onClick={() => analyzeMutation.mutate()}
            disabled={analyzeMutation.isPending}
          >
            {analyzeMutation.isPending ? "Analyse en cours…" : "Reclasser la bibliothèque"}
          </button>
        </div>
        {analyzeMutation.isError && (
          <p className={styles.error}>
            {(analyzeMutation.error as { response?: { status?: number } }).response?.status === 503
              ? "Jev n'est pas configuré : renseignez AI_GATEWAY_API_KEY dans backend/.env."
              : "L'analyse a échoué."}
          </p>
        )}
        {report && (
          <p className={styles.hint}>
            {report.analyzed} analysée{report.analyzed !== 1 ? "s" : ""} · {report.auto_classified} classée{report.auto_classified !== 1 ? "s" : ""} automatiquement
            · {report.suggested} suggestion{report.suggested !== 1 ? "s" : ""} à valider
            {report.failed > 0 && ` · ${report.failed} échec${report.failed !== 1 ? "s" : ""}`}
          </p>
        )}
      </section>
    </div>
  );
}
