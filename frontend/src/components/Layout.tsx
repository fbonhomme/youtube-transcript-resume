import { Outlet, NavLink } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getStats } from "../api/stats";
import styles from "./Layout.module.css";

function CostBadge() {
  const { data } = useQuery({
    queryKey: ["stats"],
    queryFn: getStats,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  if (!data) return null;
  const cost = data.total_cost_usd;
  const label = cost < 0.01 ? "< $0.01" : `$${cost.toFixed(2)}`;

  return (
    <span
      className={styles.cost}
      title={`${data.total_summaries} synthèses · ${data.total_input_tokens.toLocaleString()} in · ${data.total_output_tokens.toLocaleString()} out`}
    >
      {label}
    </span>
  );
}

export default function Layout() {
  return (
    <div className={styles.root}>
      <div className={styles.glow} aria-hidden="true" />
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
          <NavLink to="/prompts" className={({ isActive }) => isActive ? styles.active : ""}>
            Prompts
          </NavLink>
        </div>

        <div className={styles.navRight}>
          <CostBadge />
          <NavLink to="/new" className={styles.cta}>+ Nouvelle synthèse</NavLink>
        </div>
      </nav>

      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
