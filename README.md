# YouTube Transcript Summarizer

Génère des synthèses structurées de vidéos YouTube à partir de leurs transcripts, via Claude (Anthropic).

**Stack :** FastAPI · SQLite · React 19 · Vite · TanStack Query

---

## Fonctionnalités

- Colle une URL YouTube → résumé court, résumé long, points clés, sections thématiques, temps de lecture estimé
- Bibliothèque de synthèses avec filtrage par thème
- Gestion de thèmes (nom, couleur, icône)
- Recherche full-text dans les synthèses
- Export en PDF depuis la page de détail (impression navigateur)
- Langues supportées : FR, EN, ES, DE, IT, PT, JA, ZH

---

## Prérequis

- Python 3.12+
- Node.js 20+
- Une clé API [Anthropic](https://console.anthropic.com/)

---

## Installation

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Renseigne ANTHROPIC_API_KEY dans .env
```

### Frontend

```bash
cd frontend
npm install
```

### Démarrage

```bash
# Lancer backend + frontend en une commande
./start.sh
```

Ou séparément :

```bash
cd backend && .venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000
cd frontend && npm run dev
```

L'interface est disponible sur `http://localhost:5173`.  
La doc API (Swagger) sur `http://localhost:8000/docs`.

---

## Structure

```
backend/
├── main.py               # Point d'entrée FastAPI + CORS
├── models.py             # Modèles SQLAlchemy (Theme, Summary)
├── schemas.py            # Schémas Pydantic
├── database.py           # Session SQLite
├── routers/
│   ├── summaries.py      # CRUD synthèses + création via Claude
│   ├── themes.py         # CRUD thèmes
│   └── search.py         # Recherche full-text
├── services/
│   ├── transcript.py     # Extraction transcript YouTube
│   └── summarizer.py     # Appel Claude (claude-opus-4-7)
└── alembic/              # Migrations DB

frontend/
└── src/
    ├── pages/            # Library, NewSummary, SummaryDetail, ThemeManager
    ├── components/       # Layout, SummaryCard, ThemeSidebar, SearchBar
    └── api/              # Clients Axios (summaries, themes)
```

---

## Variables d'environnement

| Variable | Description | Exemple |
|---|---|---|
| `ANTHROPIC_API_KEY` | Clé API Anthropic | `sk-ant-...` |
| `DATABASE_URL` | URL SQLAlchemy | `sqlite:///./yt_summaries.db` |

---

## API

| Méthode | Route | Description |
|---|---|---|
| `POST` | `/summaries/` | Crée une synthèse depuis une URL YouTube |
| `GET` | `/summaries/` | Liste les synthèses (filtre `theme_id`) |
| `GET` | `/summaries/{id}` | Détail d'une synthèse |
| `PATCH` | `/summaries/{id}` | Modifie thème ou tags |
| `DELETE` | `/summaries/{id}` | Supprime une synthèse |
| `GET` | `/themes/` | Liste les thèmes |
| `POST` | `/themes/` | Crée un thème |
| `PUT` | `/themes/{id}` | Modifie un thème |
| `DELETE` | `/themes/{id}` | Supprime un thème |
| `GET` | `/search/` | Recherche (`?q=...`) |
