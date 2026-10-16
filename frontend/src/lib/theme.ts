export type Theme = "light" | "dark";

const STORAGE_KEY = "yt-theme";

/** Thème courant, tel que posé sur <html> par le script d'index.html. */
export function currentTheme(): Theme {
  return document.documentElement.dataset.theme === "light" ? "light" : "dark";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // stockage indisponible (navigation privée) : le choix vaut pour la session
  }
}
