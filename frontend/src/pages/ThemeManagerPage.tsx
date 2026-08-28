import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listThemes, createTheme, updateTheme, deleteTheme } from "../api/themes";
import type { Theme } from "../api/themes";
import { useConfirm } from "../components/ConfirmDialog";
import styles from "./ThemeManagerPage.module.css";

const COLORS = ["#6366f1","#f43f5e","#10b981","#f59e0b","#3b82f6","#8b5cf6","#ec4899","#14b8a6"];

function ThemeForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: Partial<Theme>;
  onSave: (data: { name: string; color: string; icon: string | null }) => void;
  onCancel?: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [color, setColor] = useState(initial?.color ?? COLORS[0]);
  const [icon, setIcon] = useState(initial?.icon ?? "");

  return (
    <form
      className={styles.form}
      onSubmit={(e) => { e.preventDefault(); onSave({ name, color, icon: icon || null }); }}
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

  const { data: themes = [] } = useQuery({ queryKey: ["themes"], queryFn: listThemes });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["themes"] });

  const createMutation = useMutation({
    mutationFn: createTheme,
    onSuccess: invalidate,
    onError: () => setError("Nom déjà utilisé ou erreur serveur."),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, ...payload }: { id: number; name: string; color: string; icon: string | null }) =>
      updateTheme(id, payload),
    onSuccess: () => { invalidate(); setEditingId(null); },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteTheme,
    onSuccess: invalidate,
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
    </div>
  );
}
