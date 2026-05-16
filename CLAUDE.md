# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Démarrage

```bash
./start.sh          # lance backend + frontend en une commande
```

Ou séparément :

```bash
# Backend
cd backend && .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend && npm run dev
```

- Frontend : http://localhost:5173
- Backend API + Swagger : http://localhost:8000/docs

## Stack

- **Backend** : FastAPI + SQLAlchemy + SQLite + Alembic + `youtube-transcript-api` + SDK Anthropic
- **Frontend** : React 19 + Vite + TanStack Query + React Router + Axios
- **Modèle Claude** : `claude-opus-4-7` avec `thinking: {type: "adaptive"}` et prompt caching sur le system prompt

## Architecture

### Flux de création d'une synthèse

`POST /summaries/` → `fetch_transcript()` (extrait le transcript + titre via oEmbed) → `generate_summary()` (appel Claude streaming) → persistance SQLite.

La génération prend 30–60 secondes selon la durée de la vidéo. Le transcript brut est stocké en base avec la synthèse.

### Backend (`backend/`)

- `main.py` — point d'entrée, CORS autorisant `http://localhost:5173` (vite dev) et `http://localhost` (frontend nginx Docker)
- `models.py` — deux tables : `Theme` (nom, couleur hex, icône emoji) et `Summary` (toutes les données générées + JSON columns pour `key_points`, `sections`, `tags`)
- `services/transcript.py` — extraction video_id depuis URLs youtube.com / youtu.be / shorts / embed, puis fetch transcript (priorité FR > EN > toute langue dispo)
- `services/summarizer.py` — prompt system caché (`cache_control: ephemeral`), réponse JSON pure streamed, avec fallback strip de fences markdown si le modèle en ajoute malgré l'instruction
- `routers/search.py` — recherche ILIKE sur `title`, `summary_short`, `summary_long`

### Frontend (`frontend/src/`)

- `api/client.ts` — instance Axios en `baseURL` relative (`""`) ; les requêtes sont proxifiées vers le backend (proxy vite en dev, nginx en Docker)
- Les pages utilisent TanStack Query pour le fetching/caching (staleTime 30s)
- `SearchBar` implémente un debounce 350ms côté local state avant de propager la valeur

## Git workflow

Toujours travailler sur une branche feature, jamais commiter directement sur `main` :

```bash
git checkout -b feat/ma-feature
# ... changements ...
git push origin feat/ma-feature
gh pr create
```

## Variables d'environnement

Copier `backend/.env.example` → `backend/.env` et renseigner :

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Clé API Anthropic (obligatoire) |
| `DATABASE_URL` | défaut : `sqlite:///./yt_summaries.db` |

## Migrations DB

```bash
cd backend
.venv/bin/alembic revision --autogenerate -m "description"
.venv/bin/alembic upgrade head
```

## Docker

L'application est packagée via `docker-compose.yml` (backend FastAPI + frontend nginx). `backend/start.sh` → `preflight.py` applique `alembic upgrade head` au démarrage du conteneur.

**Définition de « terminé » :** lorsque le développement d'une évolution est **complètement terminé** (code livré, tests verts, revue faite), mettre à jour la version Docker — reconstruire les images et vérifier que la stack démarre :

```bash
docker compose build
docker compose up -d   # vérifier /health, migration appliquée, puis docker compose down si besoin
```

Ne pas considérer une tâche comme finie tant que la version Docker n'a pas été mise à jour et vérifiée.
