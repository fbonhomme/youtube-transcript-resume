# YouTube Transcript Summarizer

Génère des synthèses structurées de vidéos YouTube à partir de leurs transcripts, via Claude (Anthropic).

**Stack :** FastAPI · SQLite · Alembic · React 19 · Vite · TanStack Query · Docker (Nginx)

---

## Fonctionnalités

- Colle une URL YouTube → résumé court, résumé long, points clés, sections thématiques, temps de lecture estimé
- Bibliothèque de synthèses avec filtrage par thème et **Quick Stats** (nombre de synthèses, temps de lecture économisé, tags)
- Vue de lecture **split-screen** : vidéo intégrée + document structuré, sommaire cliquable
- **Like / dislike** sur chaque synthèse
- **Prompts personnalisables** : éditeur de prompts système, prompt par défaut sélectionnable
- Gestion de thèmes (nom, couleur, icône)
- Recherche full-text dans les synthèses
- Langues supportées : FR, EN, ES, DE, IT, PT, JA, ZH

---

## Prérequis

- Python 3.12+
- Node.js 20+
- Une clé API [Anthropic](https://console.anthropic.com/)
- (Optionnel) Docker + Docker Compose pour le déploiement conteneurisé

---

## Démarrage rapide (Docker)

```bash
cp backend/.env.example backend/.env
# Renseigne ANTHROPIC_API_KEY dans backend/.env

docker compose build
docker compose up -d
```

- Application : `http://localhost`
- Le backend applique automatiquement les migrations au démarrage (`preflight.py`).
- Les données SQLite sont persistées dans le volume `db_data`.

---

## Installation (développement)

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Renseigne ANTHROPIC_API_KEY dans .env

uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

L'interface est disponible sur `http://localhost:5173` (proxy vers le backend `:8000`).
La doc API (Swagger) sur `http://localhost:8000/docs`.

### Tests backend

```bash
cd backend
pip install -r requirements-dev.txt   # ajoute pytest aux deps runtime
pytest
```

---

## Structure

```
backend/
├── main.py               # Point d'entrée FastAPI + CORS
├── models.py             # Modèles SQLAlchemy (Theme, Summary, Prompt)
├── schemas.py            # Schémas Pydantic
├── database.py           # Session SQLite
├── preflight.py          # Applique alembic upgrade au démarrage
├── start.sh              # Entrée conteneur (preflight + uvicorn)
├── routers/
│   ├── summaries.py      # CRUD synthèses + création via Claude
│   ├── themes.py         # CRUD thèmes
│   ├── prompts.py        # CRUD prompts système
│   ├── search.py         # Recherche full-text
│   └── stats.py          # Statistiques agrégées
├── services/
│   ├── transcript.py     # Extraction transcript YouTube
│   └── summarizer.py     # Appel Claude (claude-opus-4-7)
├── tests/                # Suite pytest (SQLite en mémoire)
└── alembic/              # Migrations DB

frontend/
└── src/
    ├── pages/            # Library, NewSummary, SummaryDetail, ThemeManager, Prompts
    ├── components/       # Layout, SummaryCard, ThemeSidebar, SearchBar, QuickStats
    └── api/              # Clients Axios (client, summaries, themes, prompts, stats)

docker-compose.yml        # Backend + frontend (Nginx)
backend/Dockerfile
frontend/Dockerfile       # Build Vite → Nginx
frontend/nginx.conf       # Sert le SPA + proxy API
```

---

## Variables d'environnement

Fichier `backend/.env` (utilisé par l'app et par `docker-compose`) :

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
| `PATCH` | `/summaries/{id}` | Modifie thème, tags ou feedback (like/dislike) |
| `DELETE` | `/summaries/{id}` | Supprime une synthèse |
| `GET` | `/themes/` | Liste les thèmes |
| `POST` | `/themes/` | Crée un thème |
| `PUT` | `/themes/{id}` | Modifie un thème |
| `DELETE` | `/themes/{id}` | Supprime un thème |
| `GET` | `/prompts/` | Liste les prompts |
| `GET` | `/prompts/{id}` | Détail d'un prompt |
| `POST` | `/prompts/` | Crée un prompt |
| `PUT` | `/prompts/{id}` | Modifie un prompt |
| `DELETE` | `/prompts/{id}` | Supprime un prompt |
| `GET` | `/search/` | Recherche (`?q=...`) |
| `GET` | `/stats/` | Statistiques agrégées (synthèses, temps de lecture, tags) |
| `GET` | `/health` | Healthcheck |
