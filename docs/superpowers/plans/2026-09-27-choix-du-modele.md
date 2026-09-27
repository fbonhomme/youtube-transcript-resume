# Choix du modèle de synthèse — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** permettre de choisir, pour chaque synthèse (création unitaire et import en lot), le modèle d'IA qui la génère — Claude Opus 4.7 en direct comme aujourd'hui, ou un modèle servi par OpenRouter — et enregistrer quel modèle a produit chaque synthèse.

**Architecture :** un catalogue de modèles figé dans le code (`services/llm_models.py`) est exposé par `GET /models/`. `generate_summary()` reçoit un `model` et aiguille : SDK Anthropic (streaming, thinking adaptatif, prompt caching — inchangé) pour `claude-opus-4-7`, API OpenRouter Chat Completions (`response_format: json_object`, coût réel lu dans `usage.cost`) pour les autres. Le frontend affiche un sélecteur mémorisé dans le navigateur.

**Tech Stack :** FastAPI, SQLAlchemy/Alembic (SQLite), httpx, SDK `anthropic`, React 19 + TanStack Query + Axios.

**Spec :** pas de document de spec séparé — les décisions ci-dessous (validées par l'utilisateur à la relecture de ce plan) en tiennent lieu.

## Décisions de conception

1. **Deux fournisseurs.** `claude-opus-4-7` reste appelé en direct via le SDK Anthropic : on garde le thinking adaptatif et le prompt caching, et le comportement actuel ne change pas. Tous les autres modèles passent par OpenRouter (`OPENROUTER_API_KEY`, déjà présente pour Jev).
2. **Catalogue figé, pas la liste complète d'OpenRouter** (458 modèles). On ne propose que des modèles vérifiés le 2026-09-27 : sortie JSON supportée (`response_format`) et contexte ≥ 400k tokens (transcripts longs) :

   | id | Libellé | Fournisseur | Prix entrée / sortie (USD / M tokens) |
   |---|---|---|---|
   | `claude-opus-4-7` | Claude Opus 4.7 *(défaut)* | anthropic | 5 / 25 |
   | `anthropic/claude-sonnet-5` | Claude Sonnet 5 | openrouter | 2 / 10 |
   | `openai/gpt-5.4-mini` | GPT-5.4 mini | openrouter | 0,75 / 4,50 |
   | `google/gemini-3.1-flash-lite` | Gemini 3.1 Flash Lite | openrouter | 0,25 / 1,50 |
   | `deepseek/deepseek-v4-flash` | DeepSeek V4 Flash | openrouter | 0,05 / 0,09 |

   Ajouter un modèle = ajouter une ligne dans `MODELS`.
3. **Coût.** OpenRouter renvoie le coût réel (`usage.cost`, vérifié par un appel test) → stocké tel quel. Pour Anthropic en direct, on corrige le tarif codé en dur : **Opus 4.7 coûte 5 $ / 25 $ par M tokens** (tarif affiché par OpenRouter pour `anthropic/claude-opus-4.7`), et non 15 $ / 75 $ comme aujourd'hui dans `_PRICE` — les coûts affichés sont actuellement surestimés ×3. Écriture cache = 1,25 × entrée (6,25 $), lecture cache = 0,1 × entrée (0,50 $). Les coûts déjà enregistrés en base ne sont pas recalculés.
4. **Traçabilité.** Nouvelle colonne `summaries.model`. Les synthèses existantes sont renseignées à `claude-opus-4-7` par la migration (seul modèle utilisé jusqu'ici).
5. **Mémoire du choix** : dernier modèle choisi gardé dans `localStorage` (clé `yt-summaries.model`), partagé entre « Nouvelle synthèse » et « Importer ». Si le modèle mémorisé n'existe plus ou n'est plus disponible → retour au modèle par défaut.
6. **Hors périmètre (YAGNI)** : modèle par défaut par prompt, statistiques de coût par modèle, régénération d'une synthèse existante avec un autre modèle. Jev n'est pas concerné.

## Global Constraints

- Branche `feat/model-selection` dans un worktree `../youtube-transcript-resume-models`, jamais de commit sur `main` (CLAUDE.md).
- Python : venv Windows `backend/.venv-win` du worktree (créé en Task 1) ; les tests se lancent depuis `backend/` avec `.venv-win/Scripts/python -m pytest -q`.
- Les tests ne doivent **jamais** appeler un vrai fournisseur : `backend/.env` contient de vraies clés, donc tout test dépendant de la disponibilité d'un modèle force `settings.openrouter_api_key` via `monkeypatch`.
- Aucune nouvelle dépendance (httpx est déjà dans `requirements.txt`).
- Textes d'interface et messages d'erreur en français, cohérents avec l'existant.
- Commits terminés par `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Définition de « terminé » (CLAUDE.md) : tests verts, revue faite, images Docker reconstruites et stack vérifiée (Task 4).

## Review Focus

1. **Le modèle renvoie autre chose que du JSON** (texte d'excuse, JSON tronqué, tableau au lieu d'objet) → HTTP 502 avec « <Libellé> a renvoyé une réponse qui n'est pas du JSON valide », jamais une 500 opaque. *(test : Task 2, `test_openrouter_invalid_json_raises` et `test_openrouter_non_object_json_raises`)*
2. **OpenRouter refuse la requête** (402 crédits épuisés, 429, 5xx) ou est injoignable → 502 avec le code et le message d'OpenRouter. *(test : Task 2, `test_openrouter_http_error_raises_with_message`, `test_openrouter_network_error_raises`, `test_summarize_generation_error_returns_502`)*
3. **Modèle OpenRouter demandé sans `OPENROUTER_API_KEY`** → 422 explicite avant tout appel, et le modèle apparaît « indisponible » (grisé) dans le sélecteur. *(test : Task 1, `test_summarize_unavailable_model_returns_422` et `test_list_models_marks_openrouter_unavailable_without_key`)*
4. **Identifiant de modèle inconnu** envoyé à l'API (ancien front, appel manuel) → 422 « Modèle inconnu ». *(test : Task 1, `test_summarize_unknown_model_returns_422`)*
5. **Synthèses antérieures** : après migration, elles affichent « Claude Opus 4.7 » ; une synthèse sans modèle (`null`) ne casse pas la fiche. *(test : Task 1, `test_migration_backfills_model` ; affichage vérifié en Task 3, étape navigateur)*

---

### Task 1 : Catalogue des modèles, colonne `model` et route `GET /models/`

**Files :**
- Create : `backend/services/llm_models.py`
- Create : `backend/routers/models.py`
- Create : `backend/alembic/versions/0005_add_summary_model.py`
- Create : `backend/tests/test_models.py`
- Modify : `backend/models.py` (classe `Summary`), `backend/schemas.py` (`SummarizeRequest`, `SummaryOut`, nouveau `ModelOut`), `backend/main.py` (inclusion du routeur), `backend/routers/summaries.py` (validation dans `summarize`), `frontend/vite.config.ts` et `frontend/nginx.conf` (proxy de `/models/`)

**Interfaces :**
- Produces :
  - `services.llm_models.LLMModel` (dataclass figée : `id: str`, `label: str`, `provider: str` — `"anthropic"` ou `"openrouter"`, `input_price: float`, `output_price: float`)
  - `services.llm_models.DEFAULT_MODEL: str = "claude-opus-4-7"`, `MODELS: tuple[LLMModel, ...]`
  - `services.llm_models.get_model(model_id: str) -> LLMModel | None`
  - `services.llm_models.is_available(model: LLMModel) -> bool`
  - `GET /models/` → `list[ModelOut]` avec `id, label, provider, input_price, output_price, available: bool, is_default: bool`
  - `SummarizeRequest.model: Optional[str] = None` ; `SummaryOut.model: Optional[str] = None`
  - Colonne `Summary.model` (`String(100)`, nullable)

- [ ] **Step 1 : Créer le worktree et l'environnement Python**

```bash
cd /d/2026/Projet/youtube-transcript-resume
git -c safe.directory='*' worktree add ../youtube-transcript-resume-models -b feat/model-selection
cd ../youtube-transcript-resume-models/backend
python -m venv .venv-win
.venv-win/Scripts/python -m pip install -q -r requirements-dev.txt -r requirements.txt
cp ../../youtube-transcript-resume/backend/.env .env
.venv-win/Scripts/python -m pytest -q
```

Expected : 31 passed (état de `main`).

- [ ] **Step 2 : Écrire les tests qui échouent** — `backend/tests/test_models.py`

```python
import sqlite3

import pytest
from alembic import command
from alembic.config import Config

from services import llm_models

_ANTHROPIC = "claude-opus-4-7"
_OPENROUTER = "google/gemini-3.1-flash-lite"
_URL = "https://www.youtube.com/watch?v=abc"


@pytest.fixture
def openrouter_key(monkeypatch):
    monkeypatch.setattr(llm_models.settings, "openrouter_api_key", "test-or-key")


@pytest.fixture
def no_openrouter_key(monkeypatch):
    monkeypatch.setattr(llm_models.settings, "openrouter_api_key", "")


def test_catalog_default_is_first_and_known():
    assert llm_models.MODELS[0].id == llm_models.DEFAULT_MODEL == _ANTHROPIC
    assert llm_models.get_model(_OPENROUTER).provider == "openrouter"
    assert llm_models.get_model("nope/nope") is None


def test_list_models(client, openrouter_key):
    r = client.get("/models/")
    assert r.status_code == 200
    body = r.json()
    assert [m["id"] for m in body] == [m.id for m in llm_models.MODELS]
    assert body[0] == {
        "id": _ANTHROPIC,
        "label": "Claude Opus 4.7",
        "provider": "anthropic",
        "input_price": 5.0,
        "output_price": 25.0,
        "available": True,
        "is_default": True,
    }
    assert all(m["available"] for m in body)
    assert sum(m["is_default"] for m in body) == 1


def test_list_models_marks_openrouter_unavailable_without_key(client, no_openrouter_key):
    body = {m["id"]: m for m in client.get("/models/").json()}
    assert body[_ANTHROPIC]["available"] is True
    assert body[_OPENROUTER]["available"] is False


def test_summarize_unknown_model_returns_422(client):
    r = client.post("/summaries/", json={"url": _URL, "model": "nope/nope"})
    assert r.status_code == 422
    assert "Modèle inconnu" in r.json()["detail"]


def test_summarize_unavailable_model_returns_422(client, no_openrouter_key):
    r = client.post("/summaries/", json={"url": _URL, "model": _OPENROUTER})
    assert r.status_code == 422
    assert "indisponible" in r.json()["detail"]


def test_migration_backfills_model(tmp_path, monkeypatch):
    db = tmp_path / "m.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db.as_posix()}")
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "0004")
    con = sqlite3.connect(db)
    con.execute(
        "INSERT INTO summaries (title, youtube_url, youtube_id, language, summary_short, summary_long)"
        " VALUES ('t', 'u', 'x', 'fr', 's', 'l')"
    )
    con.commit()
    con.close()

    command.upgrade(cfg, "head")

    con = sqlite3.connect(db)
    assert con.execute("SELECT model FROM summaries").fetchone() == (_ANTHROPIC,)
    con.close()
```

- [ ] **Step 3 : Vérifier l'échec**

Run : `.venv-win/Scripts/python -m pytest tests/test_models.py -q`
Expected : FAIL — `ImportError: cannot import name 'llm_models' from 'services'`.

- [ ] **Step 4 : Implémenter le catalogue** — `backend/services/llm_models.py`

```python
"""Catalogue des modèles proposés pour générer les synthèses.

Les prix (USD par million de tokens) sont indicatifs, pour l'interface : le
coût réellement facturé est calculé à la génération (voir summarizer).
Catalogue vérifié le 2026-09-27 : sortie JSON supportée, contexte >= 400k.
"""
from dataclasses import dataclass

from config import settings


@dataclass(frozen=True)
class LLMModel:
    id: str
    label: str
    provider: str  # "anthropic" (SDK direct) | "openrouter"
    input_price: float
    output_price: float


DEFAULT_MODEL = "claude-opus-4-7"

MODELS: tuple[LLMModel, ...] = (
    LLMModel("claude-opus-4-7", "Claude Opus 4.7", "anthropic", 5.0, 25.0),
    LLMModel("anthropic/claude-sonnet-5", "Claude Sonnet 5", "openrouter", 2.0, 10.0),
    LLMModel("openai/gpt-5.4-mini", "GPT-5.4 mini", "openrouter", 0.75, 4.5),
    LLMModel("google/gemini-3.1-flash-lite", "Gemini 3.1 Flash Lite", "openrouter", 0.25, 1.5),
    LLMModel("deepseek/deepseek-v4-flash", "DeepSeek V4 Flash", "openrouter", 0.05, 0.09),
)

_BY_ID = {m.id: m for m in MODELS}


def get_model(model_id: str) -> LLMModel | None:
    return _BY_ID.get(model_id)


def is_available(model: LLMModel) -> bool:
    if model.provider == "openrouter":
        return bool(settings.openrouter_api_key)
    return bool(settings.anthropic_api_key)
```

- [ ] **Step 5 : Schémas** — dans `backend/schemas.py`

Ajouter après la section Theme :

```python
# ── Model ────────────────────────────────────────────────────────────────────

class ModelOut(BaseModel):
    id: str
    label: str
    provider: str
    input_price: float
    output_price: float
    available: bool
    is_default: bool
```

Dans `SummarizeRequest`, après `tags: list[str] = []` :

```python
    model: Optional[str] = None  # None = modèle par défaut
```

Dans `SummaryOut`, après `cost_usd: Optional[float]` :

```python
    model: Optional[str] = None
```

- [ ] **Step 6 : Routeur** — `backend/routers/models.py`

```python
from fastapi import APIRouter

from schemas import ModelOut
from services.llm_models import DEFAULT_MODEL, MODELS, is_available

router = APIRouter()


@router.get("/", response_model=list[ModelOut])
def list_models():
    return [
        ModelOut(
            id=m.id,
            label=m.label,
            provider=m.provider,
            input_price=m.input_price,
            output_price=m.output_price,
            available=is_available(m),
            is_default=m.id == DEFAULT_MODEL,
        )
        for m in MODELS
    ]
```

Dans `backend/main.py` : remplacer `from routers import summaries, themes, search, prompts, stats` par `from routers import summaries, themes, search, prompts, stats, models`, et ajouter après l'inclusion de `stats.router` :

```python
app.include_router(models.router, prefix="/models", tags=["models"])
```

- [ ] **Step 7 : Validation dans `summarize`** — `backend/routers/summaries.py`

Ajouter l'import `from services.llm_models import DEFAULT_MODEL, get_model, is_available`, puis en tout début de `summarize()` (avant la vérification du thème) :

```python
    llm = get_model(payload.model or DEFAULT_MODEL)
    if llm is None:
        raise HTTPException(status_code=422, detail=f"Modèle inconnu : {payload.model}")
    if not is_available(llm):
        raise HTTPException(
            status_code=422,
            detail=f"Modèle indisponible : clé API manquante pour {llm.label}",
        )
```

(`llm` sera transmis à la génération en Task 2.)

- [ ] **Step 8 : Colonne et migration**

Dans `backend/models.py`, classe `Summary`, après `cost_usd = Column(Float, nullable=True)` :

```python
    model = Column(String(100), nullable=True)  # id du catalogue services/llm_models.py
```

`backend/alembic/versions/0005_add_summary_model.py` :

```python
"""add summaries.model (modèle ayant généré la synthèse)

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-27
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_cols = [c["name"] for c in inspector.get_columns("summaries")]
    if "model" not in existing_cols:
        with op.batch_alter_table("summaries") as batch_op:
            batch_op.add_column(sa.Column("model", sa.String(100), nullable=True))
    # Jusqu'ici toutes les synthèses étaient générées par Claude Opus 4.7.
    op.execute("UPDATE summaries SET model = 'claude-opus-4-7' WHERE model IS NULL")


def downgrade() -> None:
    with op.batch_alter_table("summaries") as batch_op:
        batch_op.drop_column("model")
```

- [ ] **Step 9 : Proxy de la nouvelle route**

`frontend/vite.config.ts` : remplacer `'^/(summaries|themes|search|prompts|stats)/'` par `'^/(summaries|themes|search|prompts|stats|models)/'`.
`frontend/nginx.conf` : remplacer `location ~ ^/(summaries|themes|search|prompts|stats)/ {` par `location ~ ^/(summaries|themes|search|prompts|stats|models)/ {`.

- [ ] **Step 10 : Vérifier le passage des tests**

Run : `.venv-win/Scripts/python -m pytest -q`
Expected : tous les tests passent (31 existants + 6 nouveaux = 37).

- [ ] **Step 11 : Commit**

```bash
git add backend/services/llm_models.py backend/routers/models.py backend/alembic/versions/0005_add_summary_model.py backend/tests/test_models.py backend/models.py backend/schemas.py backend/main.py backend/routers/summaries.py frontend/vite.config.ts frontend/nginx.conf
git commit -m "feat: catalogue des modèles de synthèse et route GET /models/

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2 : Génération via OpenRouter, coût réel et erreurs lisibles

**Files :**
- Modify : `backend/services/summarizer.py`, `backend/routers/summaries.py`
- Create : `backend/tests/test_summarizer_models.py`

**Interfaces :**
- Consumes : `get_model`, `DEFAULT_MODEL`, `LLMModel` (Task 1) ; `settings.openrouter_api_key` (existant).
- Produces :
  - `generate_summary(transcript, title, language="fr", system_prompt=None, existing_tags=None, model: str = DEFAULT_MODEL) -> tuple[dict, dict]` — même forme de retour qu'aujourd'hui (`usage` = `input_tokens`, `output_tokens`, `cost_usd`).
  - `services.summarizer.SummaryGenerationError(Exception)` — message affichable tel quel.
  - `services.summarizer.anthropic_cost(input_tokens, output_tokens, cache_write, cache_read) -> float`
  - `services.summarizer._openrouter_transport` (transport httpx injectable, tests uniquement)
  - `summaries.model` renseigné à la création ; erreurs de génération → HTTP 502.

- [ ] **Step 1 : Écrire les tests qui échouent** — `backend/tests/test_summarizer_models.py`

```python
import json

import httpx
import pytest

from services import llm_models, summarizer
from services.summarizer import SummaryGenerationError, anthropic_cost, generate_summary

_OPENROUTER = "google/gemini-3.1-flash-lite"
_URL = "https://www.youtube.com/watch?v=abc"
_RESULT = {
    "summary_short": "court",
    "summary_long": "long",
    "key_points": ["a", "b"],
    "sections": [{"title": "S", "content": "C"}],
    "duration_read": 4,
    "tags": ["ia", "ia", "docker"],
}


@pytest.fixture
def openrouter(monkeypatch):
    """Simule OpenRouter ; `reply` fixe la réponse, `seen` capture la requête."""
    monkeypatch.setattr(summarizer.settings, "openrouter_api_key", "test-or-key")
    state = {"reply": httpx.Response(200, json={}), "seen": None}

    def handler(request: httpx.Request) -> httpx.Response:
        state["seen"] = request
        return state["reply"]

    monkeypatch.setattr(summarizer, "_openrouter_transport", httpx.MockTransport(handler))
    return state


def _chat_reply(content: str, cost: float = 0.00042) -> httpx.Response:
    return httpx.Response(200, json={
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 1200, "completion_tokens": 300, "cost": cost},
    })


def test_anthropic_cost_uses_opus_4_7_pricing():
    assert anthropic_cost(1_000_000, 0, 0, 0) == pytest.approx(5.0)
    assert anthropic_cost(0, 1_000_000, 0, 0) == pytest.approx(25.0)
    assert anthropic_cost(0, 0, 1_000_000, 0) == pytest.approx(6.25)
    assert anthropic_cost(0, 0, 0, 1_000_000) == pytest.approx(0.50)


@pytest.mark.anyio
async def test_openrouter_generation(openrouter):
    openrouter["reply"] = _chat_reply(json.dumps(_RESULT))
    data, usage = await generate_summary("transcript", "Titre", model=_OPENROUTER)

    assert data["summary_short"] == "court"
    assert data["tags"] == ["ia", "docker"]
    assert usage == {"input_tokens": 1200, "output_tokens": 300, "cost_usd": 0.00042}

    req = openrouter["seen"]
    assert str(req.url) == "https://openrouter.ai/api/v1/chat/completions"
    assert req.headers["authorization"] == "Bearer test-or-key"
    body = json.loads(req.read())
    assert body["model"] == _OPENROUTER
    assert body["response_format"] == {"type": "json_object"}
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    assert "Titre" in body["messages"][1]["content"]


@pytest.mark.anyio
async def test_openrouter_fenced_json_is_accepted(openrouter):
    openrouter["reply"] = _chat_reply("```json\n" + json.dumps(_RESULT) + "\n```")
    data, _ = await generate_summary("t", "T", model=_OPENROUTER)
    assert data["duration_read"] == 4


@pytest.mark.anyio
async def test_openrouter_invalid_json_raises(openrouter):
    openrouter["reply"] = _chat_reply("Désolé, je ne peux pas résumer cette vidéo.")
    with pytest.raises(SummaryGenerationError, match="Gemini 3.1 Flash Lite a renvoyé une réponse qui n'est pas du JSON valide"):
        await generate_summary("t", "T", model=_OPENROUTER)


@pytest.mark.anyio
async def test_openrouter_non_object_json_raises(openrouter):
    openrouter["reply"] = _chat_reply("[1, 2, 3]")
    with pytest.raises(SummaryGenerationError, match="pas du JSON valide"):
        await generate_summary("t", "T", model=_OPENROUTER)


@pytest.mark.anyio
async def test_openrouter_http_error_raises_with_message(openrouter):
    openrouter["reply"] = httpx.Response(402, json={"error": {"message": "Insufficient credits"}})
    with pytest.raises(SummaryGenerationError, match=r"\(402\).*Insufficient credits"):
        await generate_summary("t", "T", model=_OPENROUTER)


@pytest.mark.anyio
async def test_openrouter_network_error_raises(monkeypatch):
    monkeypatch.setattr(summarizer.settings, "openrouter_api_key", "test-or-key")

    def handler(request):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(summarizer, "_openrouter_transport", httpx.MockTransport(handler))
    with pytest.raises(SummaryGenerationError, match="OpenRouter injoignable"):
        await generate_summary("t", "T", model=_OPENROUTER)


# ── Route ────────────────────────────────────────────────────────────────────

@pytest.fixture
def fake_transcript(monkeypatch):
    async def fake(url):
        return {"transcript": "blabla", "title": "Vidéo", "video_id": "abc"}

    monkeypatch.setattr("routers.summaries.fetch_transcript", fake)


def _fake_generate(monkeypatch, exc: Exception | None = None):
    calls = []

    async def fake(**kw):
        calls.append(kw)
        if exc:
            raise exc
        return (
            {k: _RESULT[k] for k in ("summary_short", "summary_long", "key_points", "sections", "duration_read")}
            | {"tags": ["ia"]},
            {"input_tokens": 1, "output_tokens": 1, "cost_usd": 0.001},
        )

    monkeypatch.setattr("routers.summaries.generate_summary", fake)
    return calls


def test_summarize_passes_and_stores_model(client, fake_transcript, monkeypatch):
    monkeypatch.setattr(llm_models.settings, "openrouter_api_key", "test-or-key")
    calls = _fake_generate(monkeypatch)
    r = client.post("/summaries/", json={"url": _URL, "model": _OPENROUTER})
    assert r.status_code == 201
    assert r.json()["model"] == _OPENROUTER
    assert calls[0]["model"] == _OPENROUTER


def test_summarize_defaults_to_opus(client, fake_transcript, monkeypatch):
    calls = _fake_generate(monkeypatch)
    r = client.post("/summaries/", json={"url": _URL})
    assert r.status_code == 201
    assert r.json()["model"] == llm_models.DEFAULT_MODEL
    assert calls[0]["model"] == llm_models.DEFAULT_MODEL


def test_summarize_generation_error_returns_502(client, fake_transcript, monkeypatch):
    monkeypatch.setattr(llm_models.settings, "openrouter_api_key", "test-or-key")
    _fake_generate(monkeypatch, SummaryGenerationError("OpenRouter a refusé la requête (402) : Insufficient credits"))
    r = client.post("/summaries/", json={"url": _URL, "model": _OPENROUTER})
    assert r.status_code == 502
    assert "402" in r.json()["detail"]
```

- [ ] **Step 2 : Vérifier l'échec**

Run : `.venv-win/Scripts/python -m pytest tests/test_summarizer_models.py -q`
Expected : FAIL — `ImportError: cannot import name 'SummaryGenerationError'`.

- [ ] **Step 3 : Réécrire la partie appel de `backend/services/summarizer.py`**

Garder à l'identique `_SYSTEM_PROMPT`, `_TAGS_RULE`, `_LANGUAGE_INSTRUCTIONS` et `get_default_system_prompt()`. Remplacer les imports, `_PRICE` et `generate_summary()` par :

```python
import json
import re

import anthropic
import httpx

from config import settings
from services.llm_models import DEFAULT_MODEL, get_model

_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
_MAX_TOKENS = 16000

# Transport httpx injectable pour les tests.
_openrouter_transport: httpx.AsyncBaseTransport | None = None

# Claude Opus 4.7 en direct (USD par million de tokens). Écriture cache =
# 1,25 × entrée, lecture cache = 0,1 × entrée.
_ANTHROPIC_PRICE = {
    "input": 5.0,
    "output": 25.0,
    "cache_write": 6.25,
    "cache_read": 0.50,
}


class SummaryGenerationError(Exception):
    """Échec de génération dont le message peut être montré à l'utilisateur."""


def anthropic_cost(input_tokens: int, output_tokens: int, cache_write: int, cache_read: int) -> float:
    return (
        input_tokens * _ANTHROPIC_PRICE["input"]
        + output_tokens * _ANTHROPIC_PRICE["output"]
        + cache_write * _ANTHROPIC_PRICE["cache_write"]
        + cache_read * _ANTHROPIC_PRICE["cache_read"]
    ) / 1_000_000
```

(… `_SYSTEM_PROMPT`, `_TAGS_RULE`, `_LANGUAGE_INSTRUCTIONS`, `get_default_system_prompt()` inchangés …)

```python
async def _call_anthropic(model_id: str, system_prompt: str, user_message: str) -> tuple[str, dict]:
    full_text = ""
    async with _client.messages.stream(
        model=model_id,
        max_tokens=_MAX_TOKENS,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        async for text in stream.text_stream:
            full_text += text
        final_msg = await stream.get_final_message()

    usage = final_msg.usage
    input_tok = getattr(usage, "input_tokens", 0) or 0
    output_tok = getattr(usage, "output_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    return full_text, {
        "input_tokens": input_tok,
        "output_tokens": output_tok,
        "cost_usd": round(anthropic_cost(input_tok, output_tok, cache_write, cache_read), 6),
    }


def _openrouter_error(resp: httpx.Response) -> str:
    try:
        return resp.json()["error"]["message"]
    except (ValueError, KeyError, TypeError):
        return resp.text[:200]


async def _call_openrouter(model_id: str, system_prompt: str, user_message: str) -> tuple[str, dict]:
    try:
        async with httpx.AsyncClient(timeout=300, transport=_openrouter_transport) as client:
            resp = await client.post(
                OPENROUTER_CHAT_URL,
                headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
                json={
                    "model": model_id,
                    "max_tokens": _MAX_TOKENS,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                },
            )
    except httpx.HTTPError as exc:
        raise SummaryGenerationError(f"OpenRouter injoignable : {exc}") from exc
    if resp.status_code != 200:
        raise SummaryGenerationError(
            f"OpenRouter a refusé la requête ({resp.status_code}) : {_openrouter_error(resp)}"
        )
    data = resp.json()
    usage = data.get("usage") or {}
    return data["choices"][0]["message"].get("content") or "", {
        "input_tokens": usage.get("prompt_tokens", 0) or 0,
        "output_tokens": usage.get("completion_tokens", 0) or 0,
        "cost_usd": round(float(usage.get("cost") or 0.0), 6),
    }


def _parse_json(text: str) -> dict:
    json_str = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", json_str)
    if match:
        json_str = match.group(1)
    result = json.loads(json_str)
    if not isinstance(result, dict):
        raise ValueError("objet JSON attendu")
    return result


async def generate_summary(
    transcript: str,
    title: str,
    language: str = "fr",
    system_prompt: str | None = None,
    existing_tags: list[str] | None = None,
    model: str = DEFAULT_MODEL,
) -> tuple[dict, dict]:
    llm = get_model(model)
    if llm is None:
        raise ValueError(f"Modèle inconnu : {model}")

    base_prompt = system_prompt if system_prompt is not None else _SYSTEM_PROMPT
    effective_prompt = base_prompt + _TAGS_RULE
    lang_instruction = _LANGUAGE_INSTRUCTIONS.get(language, _LANGUAGE_INSTRUCTIONS["fr"])
    tags_hint = ", ".join(sorted(existing_tags)) if existing_tags else "(aucun pour le moment)"
    user_message = (
        f"Video title: {title}\n\n"
        f"Language instruction: {lang_instruction}\n\n"
        f"Tags déjà existants dans la bibliothèque : {tags_hint}\n\n"
        f"Transcript:\n{transcript}"
    )

    call = _call_openrouter if llm.provider == "openrouter" else _call_anthropic
    full_text, usage_data = await call(llm.id, effective_prompt, user_message)

    try:
        result = _parse_json(full_text)
    except ValueError as exc:  # json.JSONDecodeError hérite de ValueError
        raise SummaryGenerationError(
            f"{llm.label} a renvoyé une réponse qui n'est pas du JSON valide"
        ) from exc

    raw_tags = [str(t).strip() for t in result.get("tags", []) if str(t).strip()]
    tags = list(dict.fromkeys(raw_tags))[:5]

    summary_data = {
        "summary_short": str(result.get("summary_short", "")),
        "summary_long": str(result.get("summary_long", "")),
        "key_points": [str(p) for p in result.get("key_points", [])],
        "sections": [
            {"title": str(s.get("title", "")), "content": str(s.get("content", ""))}
            for s in result.get("sections", [])
        ],
        "duration_read": int(result.get("duration_read", 5)),
        "tags": tags,
    }

    return summary_data, usage_data
```

- [ ] **Step 4 : Brancher la route** — `backend/routers/summaries.py`

Remplacer `from services.summarizer import generate_summary` par `from services.summarizer import SummaryGenerationError, generate_summary`, puis remplacer l'appel à `generate_summary(...)` dans `summarize()` par :

```python
    try:
        result, usage = await generate_summary(
            transcript=transcript_data["transcript"],
            title=transcript_data["title"],
            language=payload.language,
            system_prompt=prompt.system_prompt if prompt else None,
            existing_tags=existing_tags,
            model=llm.id,
        )
    except SummaryGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
```

et ajouter `model=llm.id,` dans le constructeur `Summary(...)`, juste après `cost_usd=usage["cost_usd"],`.

- [ ] **Step 5 : Vérifier le passage des tests**

Run : `.venv-win/Scripts/python -m pytest -q`
Expected : tous les tests passent (37 + 10 nouveaux = 47).

- [ ] **Step 6 : Vérification réelle (une vidéo courte, ~0,001 $)**

Avec la clé OpenRouter du `.env`, depuis `backend/` :

```bash
.venv-win/Scripts/python - <<'EOF'
import asyncio
from services.summarizer import generate_summary
data, usage = asyncio.run(generate_summary(
    "Docker permet d'empaqueter une application et ses dépendances dans un conteneur. "
    "On écrit un Dockerfile, on construit une image, puis on lance des conteneurs.",
    "Docker en 1 minute", model="google/gemini-3.1-flash-lite"))
print(data["summary_short"]); print(data["tags"]); print(usage)
EOF
```

Expected : un résumé en français, 2 à 5 tags, `cost_usd` > 0 et < 0,01.

- [ ] **Step 7 : Commit**

```bash
git add backend/services/summarizer.py backend/routers/summaries.py backend/tests/test_summarizer_models.py
git commit -m "feat: génération des synthèses via OpenRouter et tarif Opus 4.7 corrigé

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3 : Sélecteur de modèle dans l'interface

**Files :**
- Create : `frontend/src/api/models.ts`, `frontend/src/lib/modelChoice.ts`, `frontend/src/components/ModelSelect.tsx`
- Modify : `frontend/src/api/summaries.ts`, `frontend/src/pages/NewSummaryPage.tsx`, `frontend/src/pages/ImportPage.tsx`, `frontend/src/pages/SummaryDetailPage.tsx`

**Interfaces :**
- Consumes : `GET /models/` et les champs `model` de Task 1–2.
- Produces : `useModelChoice(): { models: LLMModel[]; model: string | undefined; setModel(id: string): void }` ; composant `<ModelSelect models value onChange disabled className />`.

Le frontend n'a pas de framework de test : la vérification se fait par `npm run build` (typecheck), `npx eslint` sur les fichiers touchés, et un contrôle dans le navigateur (étape 7).

- [ ] **Step 1 : Client API** — `frontend/src/api/models.ts`

```ts
import api from "./client";

export interface LLMModel {
  id: string;
  label: string;
  provider: "anthropic" | "openrouter";
  input_price: number;
  output_price: number;
  available: boolean;
  is_default: boolean;
}

export const listModels = () => api.get<LLMModel[]>("/models/").then((r) => r.data);
```

Dans `frontend/src/api/summaries.ts` : ajouter `model?: string;` à `SummarizeRequest`, et `model: string | null;` à `SummaryOut` (après `output_tokens`).

- [ ] **Step 2 : Choix mémorisé** — `frontend/src/lib/modelChoice.ts`

```ts
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listModels } from "../api/models";
import type { LLMModel } from "../api/models";

const STORAGE_KEY = "yt-summaries.model";

function readStored(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeStored(id: string) {
  try {
    localStorage.setItem(STORAGE_KEY, id);
  } catch {
    // stockage indisponible (navigation privée…) : le choix ne sera pas mémorisé
  }
}

// Modèle mémorisé s'il est toujours proposé et disponible, sinon le défaut.
export function resolveModel(models: LLMModel[], stored: string | null): string | undefined {
  const usable = models.filter((m) => m.available);
  return (usable.find((m) => m.id === stored) ?? usable.find((m) => m.is_default) ?? usable[0])?.id;
}

export function useModelChoice() {
  const { data: models = [] } = useQuery({ queryKey: ["models"], queryFn: listModels });
  const [stored, setStored] = useState<string | null>(readStored);
  const setModel = (id: string) => {
    setStored(id);
    writeStored(id);
  };
  return { models, model: resolveModel(models, stored), setModel };
}

export const formatPrice = (m: LLMModel) =>
  `${m.input_price.toLocaleString("fr-FR")} $ / ${m.output_price.toLocaleString("fr-FR")} $ par M tokens`;
```

- [ ] **Step 3 : Composant** — `frontend/src/components/ModelSelect.tsx`

```tsx
import type { LLMModel } from "../api/models";
import { formatPrice } from "../lib/modelChoice";

interface Props {
  models: LLMModel[];
  value: string | undefined;
  onChange: (id: string) => void;
  disabled?: boolean;
  className?: string;
}

export default function ModelSelect({ models, value, onChange, disabled, className }: Props) {
  const current = models.find((m) => m.id === value);
  return (
    <select
      name="model"
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
      className={className}
      disabled={disabled || models.length === 0}
      title={current ? formatPrice(current) : undefined}
    >
      {models.map((m) => (
        <option key={m.id} value={m.id} disabled={!m.available}>
          {m.label}
          {m.is_default ? " (défaut)" : ""}
          {m.available ? ` — ${m.input_price.toLocaleString("fr-FR")} $ / ${m.output_price.toLocaleString("fr-FR")} $` : " — clé API manquante"}
        </option>
      ))}
    </select>
  );
}
```

- [ ] **Step 4 : Page « Nouvelle synthèse »** — `frontend/src/pages/NewSummaryPage.tsx`

Ajouter les imports :

```tsx
import ModelSelect from "../components/ModelSelect";
import { useModelChoice } from "../lib/modelChoice";
```

Dans le composant, après `const { data: prompts = [] } = ...` :

```tsx
  const { models, model, setModel } = useModelChoice();
```

Dans `handleSubmit`, remplacer l'appel `mutation.mutate({...})` par :

```tsx
    mutation.mutate({ url: url.trim(), language, theme_id: themeId, prompt_id: promptId, tags, model });
```

Dans le premier `<div className={styles.row}>`, ajouter en dernier champ (après le bloc « Prompt ») :

```tsx
            <div className={styles.field}>
              <span className={styles.fieldLabel}>Modèle</span>
              <ModelSelect
                models={models}
                value={model}
                onChange={setModel}
                className={styles.select}
                disabled={mutation.isPending}
              />
            </div>
```

- [ ] **Step 5 : Page « Importer »** — `frontend/src/pages/ImportPage.tsx`

Mêmes deux imports que l'étape 4. Après `const [themeId, setThemeId] = ...` :

```tsx
  const { models, model, setModel } = useModelChoice();
```

Remplacer `await createSummary({ url: it.url, theme_id: themeId, tags });` par :

```tsx
        await createSummary({ url: it.url, theme_id: themeId, tags, model });
```

Et dans le `<div className={styles.row}>` de la carte d'options, ajouter après le champ « Thème » :

```tsx
              <div className={styles.field}>
                <span className={styles.fieldLabel}>Modèle</span>
                <ModelSelect
                  models={models}
                  value={model}
                  onChange={setModel}
                  className={styles.select}
                  disabled={generating}
                />
              </div>
```

- [ ] **Step 6 : Fiche d'une synthèse** — `frontend/src/pages/SummaryDetailPage.tsx`

Ajouter l'import `import { listModels } from "../api/models";`. Après la requête `themes` :

```tsx
  const { data: models = [] } = useQuery({ queryKey: ["models"], queryFn: listModels });
```

Dans `<div className={styles.pills}>`, après la pastille de langue :

```tsx
            {summary.model && (
              <span className={styles.pill}>
                {models.find((m) => m.id === summary.model)?.label ?? summary.model}
              </span>
            )}
```

- [ ] **Step 7 : Vérifier**

```bash
cd frontend
npm run build
npx eslint src/api/models.ts src/lib/modelChoice.ts src/components/ModelSelect.tsx src/pages/NewSummaryPage.tsx src/pages/ImportPage.tsx src/pages/SummaryDetailPage.tsx
```

Expected : build OK ; ESLint ne signale que l'erreur **préexistante** `NewSummaryPage.tsx:56` (`react-hooks/set-state-in-effect`), aucune nouvelle.

Puis lancer backend (`.venv-win/Scripts/uvicorn main:app --port 8000`) et frontend (`npm run dev`) du worktree sur une **copie** de la base (appliquer `alembic upgrade head` dessus) et vérifier dans le navigateur :
- « Nouvelle synthèse » : le sélecteur liste les 5 modèles, Opus marqué « (défaut) » ;
- générer une synthèse d'une vidéo courte avec « Gemini 3.1 Flash Lite » → la fiche affiche la pastille « Gemini 3.1 Flash Lite » et un coût de l'ordre du centième de centime ;
- recharger la page : le choix Gemini est conservé ; la page « Importer » propose le même choix ;
- une ancienne synthèse affiche la pastille « Claude Opus 4.7 ».

- [ ] **Step 8 : Commit**

```bash
git add frontend/src
git commit -m "feat: sélecteur de modèle (nouvelle synthèse, import) et modèle affiché sur la fiche

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4 : Livraison — PR, fusion et Docker

**Files :** aucun fichier de code.

- [ ] **Step 1 : Revue de la branche** — lancer une revue de code complète de `feat/model-selection` (skill `superpowers:requesting-code-review`) et corriger les points confirmés.

- [ ] **Step 2 : PR et fusion (après accord de l'utilisateur)**

```bash
git -c safe.directory='*' -c credential.helper= -c credential.helper='!gh auth git-credential' push https://github.com/fbonhomme/youtube-transcript-resume.git feat/model-selection
gh pr create --repo fbonhomme/youtube-transcript-resume --base main --head feat/model-selection --title "feat: choix du modèle de synthèse (Anthropic direct ou OpenRouter)"
gh pr merge <n°> --repo fbonhomme/youtube-transcript-resume --merge
```

Puis mettre à jour `main` en local (`git pull --ff-only` via HTTPS comme ci-dessus).

- [ ] **Step 3 : Docker (définition de « terminé » du CLAUDE.md)**

```bash
docker compose cp backend:/app/data/yt_summaries.db backend/docker-backup-before-models-<date>.db
docker compose build
docker compose up -d
curl -s localhost/health
curl -s localhost/models/
```

Expected : `{"status":"ok"}` ; les logs backend montrent `Running upgrade 0004 -> 0005` ; `/models/` liste 5 modèles tous `"available": true` ; les synthèses existantes ont `model = 'claude-opus-4-7'`.

- [ ] **Step 4 : Nettoyage** — supprimer le worktree et la branche (locale et distante), comme pour la fonctionnalité Jev.
