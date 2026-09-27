import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { deleteApiKey, getAdminKeys, saveApiKey, testApiKey } from "../api/admin";
import type { ApiKeyStatus, ApiKeyTestResult } from "../api/admin";
import { useConfirm } from "../components/ConfirmDialog";
import styles from "./AdminPage.module.css";

const SOURCE_LABEL: Record<ApiKeyStatus["source"], string> = {
  interface: "Saisie ici",
  env: "Fichier .env",
  none: "Non configurée",
};

const errorDetail = (err: unknown) =>
  (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;

function KeyRow({ status, canSave }: { status: ApiKeyStatus; canSave: boolean }) {
  const queryClient = useQueryClient();
  const confirm = useConfirm();
  const [value, setValue] = useState("");
  const [error, setError] = useState("");
  const [testResult, setTestResult] = useState<ApiKeyTestResult | null>(null);

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["admin-keys"] });
    queryClient.invalidateQueries({ queryKey: ["models"] });
  };

  const save = useMutation({
    mutationFn: () => saveApiKey(status.provider, value),
    onSuccess: () => { setValue(""); setError(""); setTestResult(null); refresh(); },
    onError: (err) => {
      const detail = errorDetail(err);
      setError(typeof detail === "string" ? detail : "Enregistrement impossible.");
    },
  });
  const remove = useMutation({
    mutationFn: () => deleteApiKey(status.provider),
    onSuccess: () => { setTestResult(null); refresh(); },
  });
  const test = useMutation({
    mutationFn: () => testApiKey(status.provider),
    onSuccess: setTestResult,
  });

  return (
    <li className={styles.row}>
      <div className={styles.rowHead}>
        <span className={styles.label}>{status.label}</span>
        <span className={`${styles.source} ${styles[status.source]}`}>{SOURCE_LABEL[status.source]}</span>
        {status.masked && <code className={styles.masked}>{status.masked}</code>}
      </div>
      {status.unreadable && (
        <p className={styles.warning}>
          La clé saisie ici est illisible (APP_SECRET_KEY a changé) : elle est ignorée. Saisissez-la de nouveau.
        </p>
      )}
      <form
        className={styles.form}
        onSubmit={(e) => { e.preventDefault(); if (value.trim()) save.mutate(); }}
      >
        <input
          type="password"
          autoComplete="off"
          name={`key-${status.provider}`}
          className={styles.input}
          placeholder={status.source === "none" ? "Coller la clé API" : "Nouvelle clé (remplace l'actuelle)"}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={!canSave || save.isPending}
        />
        <button type="submit" className={`${styles.btnPrimary} u-pill-btn`} disabled={!canSave || !value.trim() || save.isPending}>
          Enregistrer
        </button>
        <button type="button" className={styles.btnGhost} onClick={() => test.mutate()} disabled={status.source === "none" || test.isPending}>
          {test.isPending ? "Test…" : "Tester"}
        </button>
        {status.source === "interface" && (
          <button
            type="button"
            className={styles.btnDanger}
            disabled={remove.isPending}
            onClick={async () => {
              if (await confirm(`Supprimer la clé saisie pour ${status.label} ? La clé du fichier .env sera utilisée si elle existe.`, { confirmLabel: "Supprimer", danger: true })) {
                remove.mutate();
              }
            }}
          >
            Supprimer
          </button>
        )}
      </form>
      {error && <p className={styles.error}>{error}</p>}
      {testResult && (
        <p className={testResult.ok ? styles.ok : styles.error}>{testResult.message}</p>
      )}
    </li>
  );
}

export default function AdminPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-keys"],
    queryFn: getAdminKeys,
    retry: false,
  });

  const forbidden = axios.isAxiosError(error) && error.response?.status === 403;

  return (
    <div className={styles.wrap}>
      <h1 className={`${styles.title} u-lime-title`}>Administration</h1>

      {isLoading && <p className={styles.hint}>Chargement…</p>}

      {forbidden && (
        <section className={`${styles.card} u-glow-surface`}>
          <h2>Accès restreint</h2>
          <p className={styles.hint}>
            L'administration n'est accessible que depuis la machine qui héberge l'application :
            ouvrez <code>http://localhost:8080/admin</code> (Docker) ou <code>http://localhost:5173/admin</code> (développement).
          </p>
        </section>
      )}

      {error && !forbidden && <p className={styles.error}>Impossible de charger les clés.</p>}

      {data && (
        <section className={`${styles.card} u-glow-surface`}>
          <h2>Clés API</h2>
          {!data.encryption_ready && (
            <p className={styles.warning}>
              Chiffrement non configuré : ajoutez <code>APP_SECRET_KEY</code> dans <code>backend/.env</code> pour
              enregistrer des clés ici. En attendant, les clés du fichier .env restent utilisées.
            </p>
          )}
          <p className={styles.hint}>
            Une clé saisie ici remplace celle du fichier .env et s'applique immédiatement. Elle est stockée chiffrée
            et n'est jamais réaffichée en entier. Jev utilise la clé OpenRouter (à défaut, Vercel AI Gateway).
          </p>
          <ul className={styles.list}>
            {data.keys.map((k) => (
              <KeyRow key={k.provider} status={k} canSave={data.encryption_ready} />
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
