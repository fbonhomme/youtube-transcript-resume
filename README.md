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
- Suivi des tokens et du coût USD par synthèse

---

## Prérequis

```bash
python --version   # 3.12+
node --version     # 20+
```

- Clé API [Anthropic](https://console.anthropic.com/) (compte avec crédits)
- (Optionnel) Docker + Docker Compose pour le déploiement conteneurisé

---

## Démarrage rapide — Docker (recommandé)

```bash
cp backend/.env.example backend/.env
# Éditer backend/.env et renseigner ANTHROPIC_API_KEY=sk-ant-...

docker compose build
docker compose up -d
```

Attendre ~10 secondes, puis vérifier :

```bash
curl http://localhost/health
# {"status":"ok"}
```

- Application : `http://localhost`
- Migrations appliquées automatiquement au démarrage (`preflight.py`).
- Données SQLite persistées dans le volume Docker `db_data`.

---

## Démarrage rapide — développement local

### 1. Cloner et configurer

```bash
git clone <url-du-repo>
cd youtube-transcript-resume

cp backend/.env.example backend/.env
# Éditer backend/.env et renseigner ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head             # crée yt_summaries.db avec toutes les tables
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Vérifier : `http://localhost:8000/health` → `{"status":"ok"}`  
Swagger UI : `http://localhost:8000/docs`

### 3. Frontend (nouveau terminal)

```bash
cd frontend
npm install
npm run dev
```

Interface : `http://localhost:5173`

### Ou en une commande (les deux simultanément)

```bash
./start.sh
```

Sortie attendue :
```
▶ Démarrage du backend...
▶ Démarrage du frontend...
  En attente.......
✓ Backend  → http://localhost:8000
✓ Frontend → http://localhost:5173
```

---

## Premier test

1. Aller sur `http://localhost:5173` → cliquer **Nouvelle synthèse**
2. Coller une URL YouTube avec sous-titres activés, ex. :
   ```
   https://www.youtube.com/watch?v=dQw4w9WgXcQ
   ```
3. Choisir la langue de sortie → **Générer**
4. Attendre 30–60 s (streaming Claude) → synthèse disponible dans la bibliothèque

Ou directement via l'API :

```bash
curl -s -X POST http://localhost:8000/summaries/ \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","language":"fr"}' \
  | python3 -m json.tool | head -20
```

---

## Tests backend

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

Les tests utilisent SQLite en mémoire — pas de clé API requise.

---

## Structure

```
backend/
├── main.py               # Point d'entrée FastAPI + CORS
├── models.py             # Modèles SQLAlchemy (Theme, Summary, Prompt)
├── schemas.py            # Schémas Pydantic
├── database.py           # Session SQLite
├── config.py             # Paramètres via pydantic-settings
├── preflight.py          # Applique alembic upgrade au démarrage Docker
├── routers/
│   ├── summaries.py      # CRUD synthèses + création via Claude
│   ├── themes.py         # CRUD thèmes
│   ├── prompts.py        # CRUD prompts système
│   ├── search.py         # Recherche full-text (ILIKE title, summary_short)
│   └── stats.py          # Statistiques agrégées
├── services/
│   ├── transcript.py     # Extraction transcript YouTube + titre oEmbed
│   └── summarizer.py     # Appel Claude streaming (claude-opus-4-7)
├── tests/                # Suite pytest
└── alembic/versions/     # Migrations DB versionnées

frontend/src/
├── pages/                # Library, NewSummary, SummaryDetail, ThemeManager, Prompts
├── components/           # Layout, SummaryCard, ThemeSidebar, SearchBar, QuickStats
└── api/                  # Clients Axios (summaries, themes, prompts, stats)

docker-compose.yml        # Backend FastAPI + Frontend Nginx
frontend/nginx.conf       # Sert le SPA + proxy /api → backend:8000
```

---

## Variables d'environnement

Fichier `backend/.env` :

| Variable | Description | Défaut |
|---|---|---|
| `ANTHROPIC_API_KEY` | Clé API Anthropic (obligatoire) | — |
| `DATABASE_URL` | URL SQLAlchemy | `sqlite:///./yt_summaries.db` |

---

## API

| Méthode | Route | Description |
|---|---|---|
| `POST` | `/summaries/` | Crée une synthèse depuis une URL YouTube |
| `GET` | `/summaries/` | Liste les synthèses (`?theme_id=`, `?skip=`, `?limit=`) |
| `GET` | `/summaries/{id}` | Détail d'une synthèse |
| `PATCH` | `/summaries/{id}` | Modifie thème, tags ou feedback (`1` like, `-1` dislike) |
| `DELETE` | `/summaries/{id}` | Supprime une synthèse |
| `GET` | `/themes/` | Liste les thèmes |
| `POST` | `/themes/` | Crée un thème |
| `PUT` | `/themes/{id}` | Modifie un thème |
| `DELETE` | `/themes/{id}` | Supprime un thème |
| `GET` | `/prompts/` | Liste les prompts |
| `POST` | `/prompts/` | Crée un prompt |
| `PUT` | `/prompts/{id}` | Modifie un prompt |
| `DELETE` | `/prompts/{id}` | Supprime un prompt |
| `GET` | `/search/?q=...` | Recherche full-text |
| `GET` | `/stats/` | Statistiques agrégées |
| `GET` | `/health` | Healthcheck |

---

## Migrations DB

```bash
cd backend
# Créer une nouvelle migration
.venv/bin/alembic revision --autogenerate -m "description"

# Appliquer
.venv/bin/alembic upgrade head
```

---

## Troubleshooting

**"Les sous-titres sont désactivés pour cette vidéo" (422)**  
→ La vidéo n'a pas de transcript disponible. Essayer une autre vidéo ou vérifier que les sous-titres auto-générés sont activés sur YouTube.

**"ANTHROPIC_API_KEY manquante" / erreur 500 à la génération**  
→ Vérifier que `backend/.env` contient bien `ANTHROPIC_API_KEY=sk-ant-...` et que le backend a été redémarré après modification.

**Port 8000 ou 5173 déjà utilisé**  
```bash
# Trouver et arrêter le process
lsof -ti:8000 | xargs kill -9
lsof -ti:5173 | xargs kill -9
```

**Logs en mode Docker**  
```bash
docker compose logs -f backend
docker compose logs -f frontend
```

**Logs en mode dev**  
```bash
tail -f /tmp/backend.log
tail -f /tmp/frontend.log
```
