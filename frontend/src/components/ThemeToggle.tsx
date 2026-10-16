import { useState } from "react";
import { applyTheme, currentTheme, type Theme } from "../lib/theme";
import styles from "./ThemeToggle.module.css";

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(currentTheme);
  const next: Theme = theme === "dark" ? "light" : "dark";
  const label = next === "light" ? "Passer en mode clair" : "Passer en mode sombre";

  return (
    <button
      type="button"
      className={styles.toggle}
      onClick={() => {
        applyTheme(next);
        setTheme(next);
      }}
      title={label}
      aria-label={label}
    >
      {theme === "dark" ? "☀" : "☾"}
    </button>
  );
}
