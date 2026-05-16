import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listPrompts, createPrompt, updatePrompt, deletePrompt } from "../api/prompts";
import type { Prompt } from "../api/prompts";
import styles from "./PromptsPage.module.css";

const DEFAULT_SYSTEM_PROMPT = `You are an expert at synthesizing YouTube video content from transcripts.
Given a transcript and video title, produce a structured JSON summary.

Your response MUST be valid JSON matching exactly this schema:
{
  "summary_short": "<2-3 sentence overview>",
  "summary_long": "<comprehensive 5-10 paragraph summary>",
  "key_points": ["<point 1>", "<point 2>", ...],
  "sections": [
    {"title": "<section title>", "content": "<section content>"},
    ...
  ],
  "duration_read": <estimated minutes to read as integer>
}

Rules:
- summary_short: 2-3 sentences, captures the essence
- summary_long: thorough coverage of all major topics discussed
- key_points: 5-10 bullet points, most important takeaways
- sections: 3-7 thematic sections with meaningful titles
- duration_read: integer, realistic reading time in minutes (1 min ≈ 200 words)
- Respond ONLY with the JSON object, no markdown fences, no preamble`;

function PromptForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: Partial<Prompt>;
  onSave: (data: { name: string; description: string; system_prompt: string; is_default: boolean }) => void;
  onCancel?: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [systemPrompt, setSystemPrompt] = useState(initial?.system_prompt ?? DEFAULT_SYSTEM_PROMPT);
  const [isDefault, setIsDefault] = useState(initial?.is_default ?? false);

  return (
    <form
      className={styles.form}
      onSubmit={(e) => {
        e.preventDefault();
        onSave({ name, description, system_prompt: systemPrompt, is_default: isDefault });
      }}
    >
      <div className={styles.formRow}>
        <input
          name="prompt-name"
          className={styles.input}
          placeholder="Nom du prompt"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <input
          name="prompt-description"
          className={styles.input}
          placeholder="Description (optionnel)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>

      <div className={styles.notice}>
        Le bloc JSON schema (<code>"summary_short"</code>, <code>"key_points"</code>, etc.) doit rester intact pour que la génération fonctionne.
      </div>

      <textarea
        name="prompt-system"
        className={styles.textarea}
        value={systemPrompt}
        onChange={(e) => setSystemPrompt(e.target.value)}
        rows={18}
        required
      />

      <div className={styles.formBottom}>
        <label className={styles.checkLabel}>
          <input
            type="checkbox"
            checked={isDefault}
            onChange={(e) => setIsDefault(e.target.checked)}
          />
          Prompt par défaut
        </label>
        <div className={styles.formActions}>
          <button type="submit" className={`${styles.btnPrimary} u-pill-btn`}>
            {initial?.id ? "Enregistrer" : "Créer"}
          </button>
          {onCancel && (
            <button type="button" className={styles.btnGhost} onClick={onCancel}>Annuler</button>
          )}
        </div>
      </div>
    </form>
  );
}

export default function PromptsPage() {
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [error, setError] = useState("");

  const { data: prompts = [] } = useQuery({ queryKey: ["prompts"], queryFn: listPrompts });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["prompts"] });

  const createMutation = useMutation({
    mutationFn: createPrompt,
    onSuccess: () => { invalidate(); setShowNew(false); },
    onError: () => setError("Nom déjà utilisé ou erreur serveur."),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, ...payload }: { id: number } & Parameters<typeof updatePrompt>[1]) =>
      updatePrompt(id, payload),
    onSuccess: () => { invalidate(); setEditingId(null); },
  });

  const deleteMutation = useMutation({
    mutationFn: deletePrompt,
    onSuccess: invalidate,
  });

  return (
    <div className={styles.wrap}>
      <h1 className={`${styles.title} u-lime-title`}>Gestion des prompts</h1>

      {!showNew && (
        <button className={`${styles.btnPrimary} u-pill-btn`} onClick={() => setShowNew(true)}>
          + Nouveau prompt
        </button>
      )}

      {showNew && (
        <section className={`${styles.card} u-glow-surface`}>
          <h2>Nouveau prompt</h2>
          {error && <p className={styles.error}>{error}</p>}
          <PromptForm
            onSave={(data) => { setError(""); createMutation.mutate(data); }}
            onCancel={() => setShowNew(false)}
          />
        </section>
      )}

      <section className={`${styles.card} u-glow-surface`}>
        <h2>Prompts existants</h2>
        {prompts.length === 0 ? (
          <p className={styles.empty}>
            Aucun prompt créé. Le prompt intégré sera utilisé par défaut.
          </p>
        ) : (
          <ul className={styles.list}>
            {prompts.map((p) => (
              <li key={p.id} className={styles.item}>
                {editingId === p.id ? (
                  <PromptForm
                    initial={p}
                    onSave={(data) => updateMutation.mutate({ id: p.id, ...data })}
                    onCancel={() => setEditingId(null)}
                  />
                ) : (
                  <div className={styles.row}>
                    <div className={styles.info}>
                      <span className={styles.promptName}>
                        {p.name}
                        {p.is_default && <span className={styles.badge}>défaut</span>}
                      </span>
                      {p.description && <span className={styles.desc}>{p.description}</span>}
                    </div>
                    <div className={styles.rowActions}>
                      {!p.is_default && (
                        <button
                          className={styles.btnGhost}
                          onClick={() => updateMutation.mutate({ id: p.id, is_default: true })}
                        >
                          Définir par défaut
                        </button>
                      )}
                      <button className={styles.btnGhost} onClick={() => setEditingId(p.id)}>
                        Modifier
                      </button>
                      <button
                        className={styles.btnGhostDanger}
                        onClick={() => { if (confirm(`Supprimer "${p.name}" ?`)) deleteMutation.mutate(p.id); }}
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
