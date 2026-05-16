# Restyle Stitch + features UI visibles — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aligner les 5 écrans sur les maquettes Stitch (deep-dark + lime, glassmorphism) et ajouter les features UI visibles : Quick Stats, vue de lecture split-screen, like/dislike, filtre Thèmes en pills.

**Architecture :** Backend FastAPI/SQLAlchemy — on étend `/stats`, on ajoute une colonne `Summary.feedback` (migration Alembic) et son endpoint PATCH. Frontend React/Vite — primitives CSS partagées dans `index.css`, puis composants par écran réutilisant ces utilitaires. Le backend est développé en TDD (harnais pytest créé en Task 0) ; le frontend est vérifié par `npm run build` + revue visuelle (pas d'infra de test front, conforme à la spec).

**Tech Stack :** Python 3 / FastAPI / SQLAlchemy 2 / Alembic / pytest ; React 19 / Vite / TanStack Query / CSS Modules.

**Spec :** `docs/superpowers/specs/2026-05-16-restyle-stitch-features-design.md`

**Convention de commit :** branche `feat/ui-restyle-stitch`. Terminer chaque message de commit par :
`Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>`

---

## File Structure

| Fichier | Rôle | Action |
|---|---|---|
| `backend/requirements.txt` | dépendances | + `pytest` |
| `backend/tests/conftest.py` | harnais pytest (SQLite mémoire, override `get_db`) | créer |
| `backend/tests/test_stats.py` | tests `/stats` | créer |
| `backend/tests/test_summary_feedback.py` | tests PATCH feedback | créer |
| `backend/schemas.py` | `StatsOut`, `SummaryUpdate`, `SummaryOut` | modifier |
| `backend/routers/stats.py` | agrégations stats | modifier |
| `backend/routers/summaries.py` | logique PATCH | modifier |
| `backend/models.py` | colonne `Summary.feedback` | modifier |
| `backend/alembic/versions/*` | migration feedback | généré |
| `frontend/src/api/stats.ts` | type `Stats` | modifier |
| `frontend/src/api/summaries.ts` | types + `updateSummary` | modifier |
| `frontend/src/index.css` | `.u-stat-card`, `.u-pill-filter`, `.u-split` | modifier |
| `frontend/src/components/QuickStats.tsx` (+ `.module.css`) | bandeau KPI | créer |
| `frontend/src/pages/LibraryPage.tsx` | intégrer QuickStats | modifier |
| `frontend/src/components/ThemeSidebar.tsx` (+ `.module.css`) | pills de filtre | modifier |
| `frontend/src/pages/SummaryDetailPage.tsx` (+ `.module.css`) | split-screen + feedback | modifier |
| `frontend/src/pages/NewSummaryPage.module.css` etc. | passe cohérence | modifier |

---

### Task 0 : Harnais de tests backend

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_smoke.py`

- [ ] **Step 1 : Ajouter pytest aux dépendances**

Dans `backend/requirements.txt`, ajouter à la fin :

```
pytest==8.3.4
```

- [ ] **Step 2 : Installer pytest**

Run: `cd backend && .venv/bin/pip install pytest==8.3.4`
Expected: `Successfully installed ... pytest-8.3.4`

- [ ] **Step 3 : Créer le harnais pytest**

Créer `backend/tests/conftest.py` :

```python
import os

# Évite l'exigence d'ANTHROPIC_API_KEY au chargement de config/summarizer.
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app

_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=_engine)
    session = _TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=_engine)


@pytest.fixture
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
```

- [ ] **Step 4 : Écrire un test de fumée**

Créer `backend/tests/test_smoke.py` :

```python
def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 5 : Vérifier que le harnais tourne**

Run: `cd backend && .venv/bin/pytest tests/test_smoke.py -v`
Expected: `1 passed`

- [ ] **Step 6 : Commit**

```bash
git add backend/requirements.txt backend/tests/conftest.py backend/tests/test_smoke.py
git commit -m "test(backend): add pytest harness with in-memory sqlite

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 1 : Étendre `GET /stats/`

**Files:**
- Create: `backend/tests/test_stats.py`
- Modify: `backend/schemas.py` (`StatsOut`)
- Modify: `backend/routers/stats.py`
- Modify: `frontend/src/api/stats.ts`

- [ ] **Step 1 : Écrire le test qui échoue**

Créer `backend/tests/test_stats.py` :

```python
from models import Summary


def _make_summary(**kw):
    base = dict(
        title="t",
        youtube_url="https://youtu.be/x",
        youtube_id="x",
        language="fr",
        summary_short="s",
        summary_long="l",
        key_points=[],
        sections=[],
        tags=[],
        duration_read=5,
    )
    base.update(kw)
    return Summary(**base)


def test_stats_read_minutes_and_tags(client, db_session):
    db_session.add(_make_summary(duration_read=4, tags=["ia", "tech"]))
    db_session.add(_make_summary(duration_read=6, tags=["tech", "veille"]))
    db_session.commit()

    resp = client.get("/stats/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_summaries"] == 2
    assert data["total_read_minutes"] == 10
    assert data["total_tags"] == 3  # ia, tech, veille (distincts)


def test_stats_empty(client):
    resp = client.get("/stats/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_summaries"] == 0
    assert data["total_read_minutes"] == 0
    assert data["total_tags"] == 0
```

- [ ] **Step 2 : Lancer le test, vérifier l'échec**

Run: `cd backend && .venv/bin/pytest tests/test_stats.py -v`
Expected: FAIL — `KeyError: 'total_read_minutes'` (ou erreur de validation `StatsOut`).

- [ ] **Step 3 : Étendre `StatsOut`**

Dans `backend/schemas.py`, remplacer la classe `StatsOut` :

```python
class StatsOut(BaseModel):
    total_summaries: int
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    total_read_minutes: int
    total_tags: int
```

- [ ] **Step 4 : Calculer les nouvelles agrégations**

Dans `backend/routers/stats.py`, remplacer le corps de `get_stats` :

```python
@router.get("/", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)):
    row = db.query(
        func.count(Summary.id),
        func.coalesce(func.sum(Summary.cost_usd), 0.0),
        func.coalesce(func.sum(Summary.input_tokens), 0),
        func.coalesce(func.sum(Summary.output_tokens), 0),
        func.coalesce(func.sum(Summary.duration_read), 0),
    ).one()

    distinct_tags: set[str] = set()
    for (tags,) in db.query(Summary.tags).all():
        if tags:
            distinct_tags.update(tags)

    return StatsOut(
        total_summaries=row[0],
        total_cost_usd=float(row[1]),
        total_input_tokens=int(row[2]),
        total_output_tokens=int(row[3]),
        total_read_minutes=int(row[4]),
        total_tags=len(distinct_tags),
    )
```

- [ ] **Step 5 : Lancer le test, vérifier le succès**

Run: `cd backend && .venv/bin/pytest tests/test_stats.py -v`
Expected: `2 passed`

- [ ] **Step 6 : Mettre à jour le type TS**

Dans `frontend/src/api/stats.ts`, remplacer l'interface `Stats` :

```ts
export interface Stats {
  total_summaries: number;
  total_cost_usd: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_read_minutes: number;
  total_tags: number;
}
```

- [ ] **Step 7 : Vérifier le build front**

Run: `cd frontend && npm run build`
Expected: build OK, aucune erreur TS.

- [ ] **Step 8 : Commit**

```bash
git add backend/schemas.py backend/routers/stats.py backend/tests/test_stats.py frontend/src/api/stats.ts
git commit -m "feat(stats): expose total_read_minutes and total_tags

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2 : Colonne `Summary.feedback` + migration

**Files:**
- Modify: `backend/models.py`
- Generated: `backend/alembic/versions/<rev>_add_summary_feedback.py`

- [ ] **Step 1 : Ajouter la colonne au modèle**

Dans `backend/models.py`, classe `Summary`, juste après la ligne
`cost_usd = Column(Float, nullable=True)`, ajouter :

```python
    feedback = Column(Integer, nullable=True)  # 1 = like, -1 = dislike, NULL = neutre
```

- [ ] **Step 2 : Générer la migration**

Run: `cd backend && .venv/bin/alembic revision --autogenerate -m "add summary feedback"`
Expected: `Generating .../versions/<rev>_add_summary_feedback.py ... done`

- [ ] **Step 3 : Vérifier la migration**

Ouvrir le fichier généré dans `backend/alembic/versions/`. `upgrade()` doit
contenir **uniquement** :

```python
op.add_column('summaries', sa.Column('feedback', sa.Integer(), nullable=True))
```

`downgrade()` doit contenir `op.drop_column('summaries', 'feedback')`. Si
d'autres changements non liés apparaissent, les supprimer manuellement du
fichier.

- [ ] **Step 4 : Appliquer la migration**

Run: `cd backend && .venv/bin/alembic upgrade head`
Expected: `Running upgrade ... -> <rev>, add summary feedback`

- [ ] **Step 5 : Commit**

```bash
git add backend/models.py backend/alembic/versions/
git commit -m "feat(db): add Summary.feedback column

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3 : Endpoint PATCH feedback

**Files:**
- Create: `backend/tests/test_summary_feedback.py`
- Modify: `backend/schemas.py` (`SummaryUpdate`, `SummaryOut`)
- Modify: `backend/routers/summaries.py` (`update_summary`)
- Modify: `frontend/src/api/summaries.ts`

- [ ] **Step 1 : Écrire les tests qui échouent**

Créer `backend/tests/test_summary_feedback.py` :

```python
from models import Summary


def _seed(db):
    s = Summary(
        title="t",
        youtube_url="https://youtu.be/x",
        youtube_id="x",
        language="fr",
        summary_short="s",
        summary_long="l",
        key_points=[],
        sections=[],
        tags=[],
        duration_read=5,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s.id


def test_set_like_then_dislike_then_neutral(client, db_session):
    sid = _seed(db_session)

    r = client.patch(f"/summaries/{sid}", json={"feedback": 1})
    assert r.status_code == 200
    assert r.json()["feedback"] == 1

    r = client.patch(f"/summaries/{sid}", json={"feedback": -1})
    assert r.json()["feedback"] == -1

    r = client.patch(f"/summaries/{sid}", json={"feedback": None})
    assert r.json()["feedback"] is None


def test_feedback_invalid_value_rejected(client, db_session):
    sid = _seed(db_session)
    r = client.patch(f"/summaries/{sid}", json={"feedback": 2})
    assert r.status_code == 422


def test_patch_without_feedback_preserves_it(client, db_session):
    sid = _seed(db_session)
    client.patch(f"/summaries/{sid}", json={"feedback": 1})
    r = client.patch(f"/summaries/{sid}", json={"tags": ["x"]})
    assert r.status_code == 200
    assert r.json()["feedback"] == 1
    assert r.json()["tags"] == ["x"]
```

- [ ] **Step 2 : Lancer les tests, vérifier l'échec**

Run: `cd backend && .venv/bin/pytest tests/test_summary_feedback.py -v`
Expected: FAIL — `feedback` absent de la réponse / non accepté.

- [ ] **Step 3 : Ajouter `feedback` aux schémas**

Dans `backend/schemas.py`, remplacer la classe `SummaryUpdate` :

```python
class SummaryUpdate(BaseModel):
    theme_id: Optional[int] = None
    tags: Optional[list[str]] = None
    feedback: Optional[int] = None

    @field_validator("feedback")
    @classmethod
    def validate_feedback(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in (-1, 1):
            raise ValueError("feedback doit valoir 1, -1 ou null")
        return v
```

Dans la classe `SummaryOut`, ajouter après `cost_usd: Optional[float]` :

```python
    feedback: Optional[int]
```

- [ ] **Step 4 : Appliquer les champs réellement fournis (sémantique PATCH)**

Dans `backend/routers/summaries.py`, fonction `update_summary`, remplacer
la ligne :

```python
    for field, value in payload.model_dump(exclude_none=True).items():
```

par :

```python
    for field, value in payload.model_dump(exclude_unset=True).items():
```

> Raison : `exclude_unset` applique uniquement les champs explicitement
> envoyés (y compris `feedback: null` pour revenir au neutre), tout en
> préservant ceux non envoyés.

- [ ] **Step 5 : Lancer les tests, vérifier le succès**

Run: `cd backend && .venv/bin/pytest tests/test_summary_feedback.py -v`
Expected: `3 passed`

- [ ] **Step 6 : Non-régression complète backend**

Run: `cd backend && .venv/bin/pytest -v`
Expected: tous les tests passent (smoke + stats + feedback).

- [ ] **Step 7 : Mettre à jour l'API TS**

Dans `frontend/src/api/summaries.ts` :

Ajouter `feedback: number | null;` dans l'interface `SummaryListItem`
(après `duration_read: number;`) **et** elle sera héritée par `SummaryOut`.

Remplacer la signature de `updateSummary` :

```ts
export const updateSummary = (
  id: number,
  payload: { theme_id?: number | null; tags?: string[]; feedback?: number | null },
) => api.patch<SummaryOut>(`/summaries/${id}`, payload).then((r) => r.data);
```

- [ ] **Step 8 : Vérifier le build front**

Run: `cd frontend && npm run build`
Expected: build OK.

- [ ] **Step 9 : Commit**

```bash
git add backend/schemas.py backend/routers/summaries.py backend/tests/test_summary_feedback.py frontend/src/api/summaries.ts
git commit -m "feat(summaries): persist like/dislike feedback via PATCH

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4 : Utilitaires CSS partagés

**Files:**
- Modify: `frontend/src/index.css`

- [ ] **Step 1 : Ajouter les 3 utilitaires**

À la fin de `frontend/src/index.css`, après le bloc `.u-pill-btn`,
ajouter :

```css
.u-stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--elev);
  padding: 18px 22px;
}
.u-stat-card .u-stat-icon {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius);
  background: var(--accent-dim);
  color: var(--accent);
  font-size: 1.1rem;
}
.u-stat-card .u-stat-value {
  font-family: var(--font-display);
  font-weight: 800;
  font-size: 1.5rem;
  line-height: 1.1;
  color: var(--text);
}
.u-stat-card .u-stat-label {
  font-size: 0.8rem;
  color: var(--text2);
}

.u-pill-filter {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--bg3);
  color: var(--text2);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 7px 14px;
  font-size: 0.85rem;
  font-weight: 500;
  transition: background .15s, color .15s, border-color .15s;
}
.u-pill-filter:hover { color: var(--text); border-color: var(--border2); }
.u-pill-filter.is-active {
  background: var(--accent);
  color: #000;
  border-color: var(--accent);
}

.u-split {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 28px;
  align-items: start;
}
@media (max-width: 1024px) {
  .u-split { grid-template-columns: 1fr; }
}
```

- [ ] **Step 2 : Vérifier le build front**

Run: `cd frontend && npm run build`
Expected: build OK.

- [ ] **Step 3 : Commit**

```bash
git add frontend/src/index.css
git commit -m "feat(ui): add shared stat-card, pill-filter, split utilities

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5 : Quick Stats sur la Bibliothèque

**Files:**
- Create: `frontend/src/components/QuickStats.tsx`
- Create: `frontend/src/components/QuickStats.module.css`
- Modify: `frontend/src/pages/LibraryPage.tsx`

- [ ] **Step 1 : Créer le module CSS**

Créer `frontend/src/components/QuickStats.module.css` :

```css
.row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
@media (max-width: 720px) {
  .row { grid-template-columns: 1fr; }
}
.text { display: flex; flex-direction: column; gap: 2px; }
```

- [ ] **Step 2 : Créer le composant**

Créer `frontend/src/components/QuickStats.tsx` :

```tsx
import { useQuery } from "@tanstack/react-query";
import { getStats } from "../api/stats";
import styles from "./QuickStats.module.css";

function formatMinutes(min: number): string {
  if (min < 60) return `${min} min`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return m ? `${h}h ${m}min` : `${h}h`;
}

export default function QuickStats() {
  const { data } = useQuery({
    queryKey: ["stats"],
    queryFn: getStats,
    staleTime: 30_000,
  });

  if (!data) return null;

  const items = [
    { icon: "▦", value: String(data.total_summaries), label: "Synthèses" },
    { icon: "◷", value: formatMinutes(data.total_read_minutes), label: "Temps de lecture économisé" },
    { icon: "#", value: String(data.total_tags), label: "Tags" },
  ];

  return (
    <div className={styles.row}>
      {items.map((it) => (
        <div key={it.label} className="u-stat-card">
          <span className="u-stat-icon">{it.icon}</span>
          <span className={styles.text}>
            <span className="u-stat-value">{it.value}</span>
            <span className="u-stat-label">{it.label}</span>
          </span>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3 : Intégrer dans LibraryPage**

Dans `frontend/src/pages/LibraryPage.tsx` :

Ajouter l'import après la ligne `import SearchBar from "../components/SearchBar";` :

```tsx
import QuickStats from "../components/QuickStats";
```

Dans le JSX, à l'intérieur de `<section className={styles.content}>`,
**avant** `<div className={styles.header}>`, insérer :

```tsx
        <QuickStats />
```

- [ ] **Step 4 : Vérifier le build front**

Run: `cd frontend && npm run build`
Expected: build OK.

- [ ] **Step 5 : Revue visuelle**

Run: `cd frontend && npm run dev` (laisser tourner, ouvrir http://localhost:5173/library)
Expected: 3 cartes stats au-dessus du titre Bibliothèque, alignées sur la maquette `biblioth_que_stats_utilisateur_desktop`.

- [ ] **Step 6 : Commit**

```bash
git add frontend/src/components/QuickStats.tsx frontend/src/components/QuickStats.module.css frontend/src/pages/LibraryPage.tsx
git commit -m "feat(ui): add Quick Stats banner on Library

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 6 : Filtre Thèmes en pills

**Files:**
- Modify: `frontend/src/components/ThemeSidebar.tsx`
- Modify: `frontend/src/components/ThemeSidebar.module.css`

- [ ] **Step 1 : Réécrire le composant avec `u-pill-filter`**

Remplacer le contenu de `frontend/src/components/ThemeSidebar.tsx` :

```tsx
import type { Theme } from "../api/themes";
import styles from "./ThemeSidebar.module.css";

interface Props {
  themes: Theme[];
  selectedId: number | null;
  onSelect: (id: number | null) => void;
}

export default function ThemeSidebar({ themes, selectedId, onSelect }: Props) {
  return (
    <aside className={styles.sidebar}>
      <p className={styles.label}>Thèmes</p>
      <div className={styles.list}>
        <button
          className={`u-pill-filter ${selectedId === null ? "is-active" : ""}`}
          onClick={() => onSelect(null)}
        >
          Tous
        </button>
        {themes.map((t) => (
          <button
            key={t.id}
            className={`u-pill-filter ${selectedId === t.id ? "is-active" : ""}`}
            onClick={() => onSelect(t.id)}
          >
            <span
              className={styles.dot}
              style={{ background: t.color }}
              aria-hidden="true"
            />
            {t.icon ? `${t.icon} ` : ""}
            <span className={styles.name}>{t.name}</span>
            <span className={styles.count}>{t.summary_count}</span>
          </button>
        ))}
      </div>
    </aside>
  );
}
```

- [ ] **Step 2 : Adapter le module CSS**

Remplacer le contenu de `frontend/src/components/ThemeSidebar.module.css` :

```css
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.label {
  font-family: var(--font-display);
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text2);
}

.list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.name { flex: 1; }

.count {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  opacity: 0.7;
}

@media (max-width: 1024px) {
  .list {
    flex-direction: row;
    flex-wrap: wrap;
  }
}
```

- [ ] **Step 3 : Vérifier le build front**

Run: `cd frontend && npm run build`
Expected: build OK.

- [ ] **Step 4 : Revue visuelle**

Ouvrir http://localhost:5173/library
Expected: filtre Thèmes en pills ; pill active = fond lime / texte noir ; clic filtre toujours la grille.

- [ ] **Step 5 : Commit**

```bash
git add frontend/src/components/ThemeSidebar.tsx frontend/src/components/ThemeSidebar.module.css
git commit -m "feat(ui): theme filter as pill chips

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 7 : Vue de lecture split-screen + feedback

**Files:**
- Modify: `frontend/src/pages/SummaryDetailPage.tsx`
- Modify: `frontend/src/pages/SummaryDetailPage.module.css`

- [ ] **Step 1 : Réécrire la page**

Remplacer le contenu de `frontend/src/pages/SummaryDetailPage.tsx` :

```tsx
import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getSummary, deleteSummary, updateSummary } from "../api/summaries";
import { listThemes } from "../api/themes";
import styles from "./SummaryDetailPage.module.css";

export default function SummaryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showTranscript, setShowTranscript] = useState(false);

  const { data: summary, isLoading } = useQuery({
    queryKey: ["summary", id],
    queryFn: () => getSummary(Number(id)),
    enabled: !!id,
  });

  const { data: themes = [] } = useQuery({ queryKey: ["themes"], queryFn: listThemes });

  const deleteMutation = useMutation({
    mutationFn: () => deleteSummary(Number(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["summaries"] });
      navigate("/library");
    },
  });

  const updateMutation = useMutation({
    mutationFn: (payload: { theme_id?: number | null; feedback?: number | null }) =>
      updateSummary(Number(id), payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["summary", id] }),
  });

  if (isLoading) return <p className={styles.loading}>Chargement…</p>;
  if (!summary) return <p className={styles.loading}>Synthèse introuvable.</p>;

  const date = new Date(summary.created_at).toLocaleDateString("fr-FR", {
    day: "2-digit", month: "long", year: "numeric",
  });

  const scrollToSection = (i: number) => {
    document.getElementById(`section-${i}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const setFeedback = (value: number) => {
    updateMutation.mutate({ feedback: summary.feedback === value ? null : value });
  };

  return (
    <div className={styles.wrap}>
      <Link to="/library" className={styles.back}>← Bibliothèque</Link>

      <div className="u-split">
        <div className={styles.left}>
          <div className={styles.player}>
            <iframe
              src={`https://www.youtube.com/embed/${summary.youtube_id}`}
              title={summary.title}
              loading="lazy"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>
          {summary.theme && (
            <span className={styles.theme} style={{ color: summary.theme.color }}>
              {summary.theme.icon} {summary.theme.name}
            </span>
          )}
          <h1 className={`${styles.title} u-lime-title`}>{summary.title}</h1>
          <p className={styles.subtitle}>{summary.summary_short}</p>
          <div className={styles.pills}>
            <span className={styles.pill}>{summary.duration_read} min de lecture</span>
            <span className={styles.pill}>{summary.language.toUpperCase()}</span>
            {summary.tags.map((t) => <span key={t} className={styles.tag}>{t}</span>)}
          </div>
          <p className={styles.date}>{date}</p>

          <div className={styles.actions}>
            <button
              className={`${styles.feedbackBtn} ${summary.feedback === 1 ? styles.liked : ""}`}
              onClick={() => setFeedback(1)}
              disabled={updateMutation.isPending}
              aria-label="J'aime"
            >
              👍
            </button>
            <button
              className={`${styles.feedbackBtn} ${summary.feedback === -1 ? styles.disliked : ""}`}
              onClick={() => setFeedback(-1)}
              disabled={updateMutation.isPending}
              aria-label="Je n'aime pas"
            >
              👎
            </button>
            <a href={summary.youtube_url} target="_blank" rel="noreferrer" className={styles.btnOutline}>
              Voir sur YouTube ↗
            </a>
          </div>

          <div className={styles.field}>
            <span className={styles.fieldLabel}>Thème</span>
            <select
              className={styles.select}
              value={summary.theme_id ?? ""}
              onChange={(e) =>
                updateMutation.mutate({ theme_id: e.target.value ? Number(e.target.value) : null })
              }
            >
              <option value="">— Aucun —</option>
              {themes.map((t) => (
                <option key={t.id} value={t.id}>{t.icon ? `${t.icon} ` : ""}{t.name}</option>
              ))}
            </select>
          </div>

          <button
            className={styles.btnDanger}
            onClick={() => { if (confirm("Supprimer cette synthèse ?")) deleteMutation.mutate(); }}
            disabled={deleteMutation.isPending}
          >
            Supprimer
          </button>
        </div>

        <div className={styles.right}>
          {summary.key_points.length > 0 && (
            <section className={styles.takeaways}>
              <h2>Key Takeaways</h2>
              <ul>
                {summary.key_points.map((p, i) => <li key={i}>{p}</li>)}
              </ul>
            </section>
          )}

          {summary.sections.length > 0 && (
            <section className={styles.toc}>
              <h2>Sommaire</h2>
              <ol>
                {summary.sections.map((s, i) => (
                  <li key={i}>
                    <button className={styles.tocLink} onClick={() => scrollToSection(i)}>
                      {s.title}
                    </button>
                  </li>
                ))}
              </ol>
            </section>
          )}

          <section className={styles.section}>
            <h2>Résumé détaillé</h2>
            <p className={styles.longText}>{summary.summary_long}</p>
          </section>

          {summary.sections.map((s, i) => (
            <section key={i} id={`section-${i}`} className={styles.section}>
              <h3 className={styles.sectionTitle}>{s.title}</h3>
              <p>{s.content}</p>
            </section>
          ))}

          <section className={styles.section}>
            <button className={styles.transcriptToggle} onClick={() => setShowTranscript((v) => !v)}>
              {showTranscript ? "Masquer" : "Afficher"} le transcript original
            </button>
            {showTranscript && (
              summary.transcript
                ? <pre className={styles.transcript}>{summary.transcript}</pre>
                : <p className={styles.noTranscript}>Transcript non disponible pour cette synthèse.</p>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2 : Réécrire le module CSS**

Remplacer le contenu de `frontend/src/pages/SummaryDetailPage.module.css` :

```css
.wrap { animation: fadeUp .3s ease both; }

.loading {
  color: var(--text2);
  padding: 60px 0;
  text-align: center;
}

.back {
  display: inline-block;
  margin-bottom: 20px;
  color: var(--text2);
  font-size: 0.85rem;
}
.back:hover { color: var(--accent); }

.left {
  position: sticky;
  top: calc(var(--nav-h) + 24px);
  display: flex;
  flex-direction: column;
  gap: 14px;
}
@media (max-width: 1024px) {
  .left { position: static; }
}

.player {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--border);
  box-shadow: var(--elev);
}
.player iframe {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border: 0;
}

.theme {
  font-size: 0.8rem;
  font-weight: 600;
}

.title {
  font-size: 1.6rem;
  line-height: 1.2;
}

.subtitle {
  color: var(--text2);
  font-size: 0.95rem;
}

.pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.pill,
.tag {
  font-size: 0.74rem;
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--bg3);
  color: var(--text2);
}
.tag { color: var(--accent); background: var(--accent-dim); }

.date {
  font-size: 0.78rem;
  color: var(--text3);
}

.actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.feedbackBtn {
  width: 40px;
  height: 40px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--bg3);
  font-size: 1rem;
  transition: background .15s, border-color .15s, transform .1s;
}
.feedbackBtn:hover { border-color: var(--border2); }
.feedbackBtn:active { transform: translateY(1px); }
.feedbackBtn:disabled { opacity: .55; cursor: not-allowed; }
.liked { background: var(--accent); border-color: var(--accent); }
.disliked { background: var(--danger); border-color: var(--danger); }

.btnOutline {
  display: inline-flex;
  align-items: center;
  padding: 8px 16px;
  border-radius: 999px;
  border: 1px solid var(--border2);
  color: var(--text);
  font-size: 0.82rem;
  font-weight: 600;
}
.btnOutline:hover { border-color: var(--accent); color: var(--accent); }

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.fieldLabel {
  font-size: 0.78rem;
  color: var(--text2);
}
.select {
  background: var(--bg3);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  font-size: 0.85rem;
}

.btnDanger {
  align-self: flex-start;
  background: var(--danger-dim);
  color: var(--danger);
  border: 1px solid transparent;
  border-radius: 999px;
  padding: 8px 16px;
  font-size: 0.82rem;
  font-weight: 600;
}
.btnDanger:hover { border-color: var(--danger); }
.btnDanger:disabled { opacity: .55; cursor: not-allowed; }

.right {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.takeaways {
  background: var(--accent-dim);
  border: 1px solid var(--accent);
  border-radius: var(--radius-lg);
  padding: 20px 24px;
}
.takeaways h2 {
  font-family: var(--font-display);
  color: var(--accent);
  font-size: 1rem;
  margin-bottom: 10px;
}
.takeaways ul { padding-left: 18px; display: flex; flex-direction: column; gap: 6px; }

.toc {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px 24px;
}
.toc h2 {
  font-family: var(--font-display);
  font-size: 1rem;
  margin-bottom: 10px;
}
.toc ol { padding-left: 18px; display: flex; flex-direction: column; gap: 4px; }
.tocLink {
  background: none;
  border: none;
  color: var(--text2);
  font-size: 0.9rem;
  text-align: left;
  padding: 0;
}
.tocLink:hover { color: var(--accent); }

.section h2,
.section h3 {
  font-family: var(--font-display);
  margin-bottom: 10px;
}
.section h2 { font-size: 1.1rem; }
.sectionTitle { font-size: 1rem; color: var(--accent); }
.longText { color: var(--text); white-space: pre-wrap; }

.transcriptToggle {
  background: var(--bg3);
  color: var(--text2);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 7px 14px;
  font-size: 0.8rem;
}
.transcriptToggle:hover { color: var(--text); }

.transcript {
  margin-top: 12px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  font-family: var(--font-mono);
  font-size: 0.78rem;
  white-space: pre-wrap;
  max-height: 360px;
  overflow: auto;
}
.noTranscript {
  margin-top: 12px;
  color: var(--text3);
  font-size: 0.85rem;
}
```

- [ ] **Step 3 : Vérifier le build front**

Run: `cd frontend && npm run build`
Expected: build OK, aucune erreur TS.

- [ ] **Step 4 : Revue visuelle**

Ouvrir une synthèse via http://localhost:5173/library puis cliquer une carte.
Expected :
- desktop : vidéo embed jouable à gauche (sticky au scroll), document à droite (Key Takeaways encadré lime, Sommaire cliquable qui scrolle vers la section, sections) ;
- 👍/👎 : clic met l'état actif (lime / rouge), recliquer le même bouton revient au neutre, l'état persiste après rafraîchissement ;
- < 1024px : empilement vertical, vidéo non-sticky.

- [ ] **Step 5 : Commit**

```bash
git add frontend/src/pages/SummaryDetailPage.tsx frontend/src/pages/SummaryDetailPage.module.css
git commit -m "feat(ui): split-screen reading view with like/dislike

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 8 : Passe de cohérence — écrans restants

**Files:**
- Modify: `frontend/src/pages/NewSummaryPage.module.css`
- Modify: `frontend/src/pages/ThemeManagerPage.module.css`
- Modify: `frontend/src/pages/PromptsPage.module.css`
- Modify (si nécessaire) : les `.tsx` correspondants pour appliquer `u-pill-btn` / `u-glow-surface` / `u-lime-title`

- [ ] **Step 1 : Auditer l'écart visuel**

Run: `cd frontend && npm run dev` puis ouvrir `/new`, `/themes`, `/prompts`.
Comparer aux maquettes `lecture_de_synth_se_vid_o_desktop` (typo/espacements),
`yt_synth_ses_dashboard_redesign_2` (Thèmes) et `configuration_des_prompts_ia`
(Prompts). Lister par écran les écarts : titres non `u-lime-title`, surfaces
non `u-glow-surface`, boutons primaires non `u-pill-btn`, échelle typo/espacement
incohérente avec Bibliothèque/Lecture.

- [ ] **Step 2 : Aligner `NewSummaryPage`**

Appliquer sur `NewSummaryPage.tsx` / `.module.css` : titre en `u-lime-title`,
conteneur de formulaire en `u-glow-surface`, bouton de soumission en
`u-pill-btn`. Ne pas changer la logique (champs, mutation, états). Aucun
nouvel appel backend.

- [ ] **Step 3 : Aligner `ThemeManagerPage`**

Idem : hero/titre en `u-lime-title`, bloc « Nouveau Thème » et « Thèmes
Existants » en `u-glow-surface`, bouton « Créer » en `u-pill-btn`,
conformément à `yt_synth_ses_dashboard_redesign_2`. Logique inchangée.

- [ ] **Step 4 : Aligner `PromptsPage`**

Idem : surfaces en `u-glow-surface`, boutons primaires en `u-pill-btn`,
titre en `u-lime-title`. **Ne pas** ajouter de « Test Preview » (hors
périmètre). Logique inchangée.

- [ ] **Step 5 : Vérifier le build front**

Run: `cd frontend && npm run build`
Expected: build OK.

- [ ] **Step 6 : Revue visuelle des 3 écrans**

Ouvrir `/new`, `/themes`, `/prompts`.
Expected : palette, surfaces, boutons et typo cohérents avec Bibliothèque
et Lecture ; aucune régression fonctionnelle.

- [ ] **Step 7 : Commit**

```bash
git add frontend/src/pages/NewSummaryPage.* frontend/src/pages/ThemeManagerPage.* frontend/src/pages/PromptsPage.*
git commit -m "feat(ui): coherence pass on New / Themes / Prompts

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 9 : Vérification finale

**Files:** aucun (vérification seule)

- [ ] **Step 1 : Suite backend complète**

Run: `cd backend && .venv/bin/pytest -v`
Expected: 100 % vert (smoke, stats, feedback).

- [ ] **Step 2 : Build front de production**

Run: `cd frontend && npm run build`
Expected: build OK, zéro erreur TS.

- [ ] **Step 3 : Checklist visuelle desktop + repli**

Lancer `./start.sh`, parcourir les 5 écrans :
- Bibliothèque : Quick Stats (3 cartes), filtre Thèmes en pills actif/inactif, grille.
- Lecture : split-screen, vidéo jouable + sticky, Key Takeaways lime, sommaire cliquable, 👍/👎 persistant, repli < 1024px.
- Nouvelle synthèse / Thèmes / Prompts : cohérence visuelle.

Noter tout écart ; corriger dans la tâche concernée si bloquant.

- [ ] **Step 4 : Commit éventuel de correctifs**

S'il y a des correctifs :

```bash
git add -A
git commit -m "fix(ui): final polish from verification pass

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Self-Review

**Couverture de la spec :**
- Design system (`u-stat-card`/`u-pill-filter`/`u-split`) → Task 4 ✔
- Backend `/stats` étendu → Task 1 ✔
- `Summary.feedback` + migration → Task 2 ✔
- PATCH feedback (1/-1/null, validation) → Task 3 ✔
- Quick Stats Bibliothèque → Task 5 ✔
- Filtre Thèmes en pills → Task 6 ✔
- Vue de lecture split-screen + feedback UI → Task 7 ✔
- Passe de cohérence New/Themes/Prompts → Task 8 ✔
- Tests backend + build front + revue visuelle → Tasks 1/3/9 ✔
- Risque embed YouTube → noté dans la spec ; fallback visuel non bloquant (l'iframe d'embed reste affichée même si la vidéo refuse la lecture, l'utilisateur a le lien « Voir sur YouTube »).

**Scan placeholders :** aucun TBD/TODO ; chaque step de code contient le code complet.

**Cohérence des types :** `feedback: number | null` (TS) ↔ `Optional[int]` (Pydantic) ↔ `Integer nullable` (SQLAlchemy) ; `total_read_minutes`/`total_tags` identiques entre `StatsOut`, router, `Stats` TS et `QuickStats`. `updateMutation` de Task 7 accepte `{ theme_id?, feedback? }`, cohérent avec la signature `updateSummary` de Task 3.
