import { Outlet, NavLink } from "react-router-dom";
import styles from "./Layout.module.css";

export default function Layout() {
  return (
    <div className={styles.root}>
      <nav className={styles.nav}>
        <div className={styles.brand}>
          <span className={styles.brandIcon}>▶</span>
          <span>YT Synthèses</span>
        </div>
        <div className={styles.links}>
          <NavLink to="/library" className={({ isActive }) => isActive ? styles.active : ""}>
            Bibliothèque
          </NavLink>
          <NavLink to="/new" className={({ isActive }) => isActive ? styles.active : ""}>
            + Nouvelle
          </NavLink>
          <NavLink to="/themes" className={({ isActive }) => isActive ? styles.active : ""}>
            Thèmes
          </NavLink>
        </div>
      </nav>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
