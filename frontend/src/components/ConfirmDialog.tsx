import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import styles from "./ConfirmDialog.module.css";

interface ConfirmOptions {
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
}

interface ConfirmState extends ConfirmOptions {
  message: string;
  resolve: (value: boolean) => void;
}

type ConfirmFn = (message: string, options?: ConfirmOptions) => Promise<boolean>;

const ConfirmContext = createContext<ConfirmFn | null>(null);

export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<ConfirmState | null>(null);
  const confirmBtnRef = useRef<HTMLButtonElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  const confirm = useCallback<ConfirmFn>((message, options) => {
    triggerRef.current = document.activeElement as HTMLElement;
    return new Promise<boolean>((resolve) => {
      setState({ message, resolve, ...options });
    });
  }, []);

  const close = useCallback((result: boolean) => {
    setState((current) => {
      current?.resolve(result);
      return null;
    });
    triggerRef.current?.focus?.();
  }, []);

  useEffect(() => {
    if (!state) return;
    confirmBtnRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") close(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [state, close]);

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      {state && (
        <div
          className={styles.backdrop}
          onMouseDown={(e) => { if (e.target === e.currentTarget) close(false); }}
        >
          <div
            className={`${styles.dialog} u-glow-surface`}
            role="alertdialog"
            aria-modal="true"
            aria-describedby="confirm-dialog-message"
          >
            <p id="confirm-dialog-message" className={styles.message}>{state.message}</p>
            <div className={styles.actions}>
              <button type="button" className={styles.cancelBtn} onClick={() => close(false)}>
                {state.cancelLabel ?? "Annuler"}
              </button>
              <button
                type="button"
                ref={confirmBtnRef}
                className={`${styles.confirmBtn} ${state.danger ? styles.danger : ""}`}
                onClick={() => close(true)}
              >
                {state.confirmLabel ?? "Confirmer"}
              </button>
            </div>
          </div>
        </div>
      )}
    </ConfirmContext.Provider>
  );
}

export function useConfirm(): ConfirmFn {
  const ctx = useContext(ConfirmContext);
  if (!ctx) throw new Error("useConfirm must be used within a ConfirmProvider");
  return ctx;
}
