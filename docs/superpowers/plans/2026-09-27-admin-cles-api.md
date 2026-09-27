# Administration des clés API — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** saisir, remplacer, supprimer et tester les clés API (Anthropic, OpenRouter — utilisée aussi par Jev —, Vercel AI Gateway) depuis une page « Administration » de l'application, sans éditer `backend/.env`, cette page n'étant accessible que depuis la machine qui héberge l'application.

**Architecture :** les clés saisies sont chiffrées (Fernet, clé maître `APP_SECRET_KEY` du `.env`) dans une table `app_settings`. Un service `services/api_keys.py` résout la clé en vigueur : clé saisie dans l'interface, sinon variable du `.env`. Les trois consommateurs (catalogue des modèles, génération, Jev) passent par ce service, donc un changement s'applique sans redémarrage. Les routes `/admin-api/…` exigent un accès local : en développement, adresse client `127.0.0.1`/`::1` ; sous Docker, un bloc nginx dédié écoute sur `127.0.0.1:8080` (inaccessible depuis le réseau) et seul lui transmet l'en-tête `X-Admin-Access: local` ; le port 80 refuse `/admin-api/`.

**Tech Stack :** FastAPI, SQLAlchemy/Alembic (SQLite), `cryptography` (Fernet), httpx, React 19 + TanStack Query, nginx, Docker Compose.

**Spec :** pas de document séparé — la section « Décisions de conception » ci-dessous, validée par l'utilisateur à la relecture, en tient lieu. Choix de protection fait par l'utilisateur : **localhost uniquement, sans mot de passe**.

## Prérequis

La branche `feat/model-selection` (catalogue `services/llm_models.py`, génération OpenRouter) doit être **fusionnée dans `main`** avant de commencer : ce plan modifie `llm_models.py` et `summarizer.py` tels qu'ils sont sur cette branche. Créer ensuite la branche `feat/admin-api-keys` depuis `main` à jour, dans le worktree `../youtube-transcript-resume-admin`.

## Décisions de conception

1. **Clés gérées** : `anthropic` (Claude en direct), `openrouter` (modèles OpenRouter **et** Jev), `ai_gateway` (Jev, secours). Jev n'a pas de clé propre.
2. **Priorité** : clé saisie dans l'interface > variable du `.env` > aucune. Supprimer une clé dans l'interface fait revenir à celle du `.env`. `ANTHROPIC_API_KEY` devient facultative dans le `.env` (l'app démarre sans ; Opus est alors indisponible tant qu'aucune clé n'est saisie).
3. **Chiffrement** : Fernet (`cryptography`), clé maître `APP_SECRET_KEY` dans le `.env` (seul secret qui y reste obligatoire pour utiliser l'administration). Sans `APP_SECRET_KEY` valide : l'app fonctionne avec les clés du `.env`, l'administration affiche les clés en lecture seule et refuse l'enregistrement (HTTP 503). Si `APP_SECRET_KEY` change, les clés déjà saisies deviennent « illisibles » : elles sont ignorées (retour au `.env`) et signalées dans la page.
4. **Jamais de clé en clair vers le navigateur** : l'API n'accepte une clé qu'en écriture et ne renvoie qu'une version masquée (`sk-or-…a3f9`).
5. **Accès localhost uniquement** (dépendance FastAPI `require_local_admin`, HTTP 403 sinon) :
   - développement : `request.client.host` ∈ {`127.0.0.1`, `::1`} — le proxy Vite se connecte depuis la machine ; un accès réseau direct au port 8000 est refusé ;
   - Docker : le backend ne voit que l'IP du conteneur nginx, donc on active `ADMIN_TRUST_PROXY_HEADER=true` (compose uniquement) et le backend accepte l'en-tête `X-Admin-Access: local`. Seul le bloc nginx du port 8080 le pose (`proxy_set_header`, qui écrase toute valeur envoyée par le client) ; ce port est publié sur `127.0.0.1:8080` uniquement. Le bloc du port 80 répond 403 à `/admin-api/` et vide cet en-tête sur les autres routes. Le port 8000 du backend n'est pas publié par compose.
   - URL d'administration : `http://localhost:8080/admin` (Docker) ou `http://localhost:5173/admin` (développement). Sur le port 80, la page `/admin` s'affiche mais indique qu'elle n'est accessible que depuis la machine.
6. **Bouton « Tester »** : appel gratuit au fournisseur avec la clé en vigueur, vérifié en réel le 2026-09-27 :
   - Anthropic : `GET https://api.anthropic.com/v1/models` (en-têtes `x-api-key`, `anthropic-version: 2023-06-01`) → 200 si valide, 401 sinon ;
   - OpenRouter : `GET https://openrouter.ai/api/v1/key` (Bearer) → 200 si valide, 401 sinon ;
   - Vercel AI Gateway : `GET https://ai-gateway.vercel.sh/v1/models` (Bearer) → 401 vérifié pour une clé invalide ; le 200 d'une clé valide n'a pas pu être vérifié (pas de clé Vercel).
7. **Hors périmètre (YAGNI)** : mot de passe administrateur, gestion d'autres réglages que les clés, historique des clés, rotation automatique de `APP_SECRET_KEY`.

## Global Constraints

- Branche `feat/admin-api-keys` dans le worktree `../youtube-transcript-resume-admin`, jamais de commit sur `main` (CLAUDE.md).
- Toute commande git préfixée par `export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0='*'` (erreur « dubious ownership » sur D:, ne pas modifier la config git globale).
- Python : venv Windows `backend/.venv-win` du worktree ; tests depuis `backend/` avec `.venv-win/Scripts/python -m pytest -q`.
- Une seule nouvelle dépendance : `cryptography==50.0.1` (version vérifiée disponible).
- Les tests n'appellent jamais un vrai fournisseur (transports httpx simulés) ; `backend/.env` contient de vraies clés.
- Une clé API en clair n'apparaît jamais dans une réponse HTTP, un log, un message d'erreur ou un commit.
- Textes et messages en français.
- Commits terminés par `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Définition de « terminé » (CLAUDE.md) : tests verts, revue faite, images Docker reconstruites et stack vérifiée (Task 6).

## Review Focus

1. **Accès depuis le réseau** : un appel à `/admin-api/…` qui ne vient pas de la machine (IP non loopback, ou en-tête `X-Admin-Access` forgé alors que la confiance au proxy est désactivée, ou valeur d'en-tête différente de `local`) → 403. *(tests : Task 3, `test_require_local_admin_*` ; vérif. nginx : Task 5 step 4 et Task 6 step 3)*
2. **Aucune fuite de clé** : après enregistrement, ni `GET /admin-api/keys/`, ni la réponse du `PUT`, ni un message d'erreur ne contiennent la clé complète. *(test : Task 3, `test_put_key_never_returns_plaintext`)*
3. **`APP_SECRET_KEY` absente ou changée** : l'app continue avec les clés du `.env` ; l'enregistrement est refusé avec un message clair ; une clé stockée devenue illisible est signalée et ignorée. *(tests : Task 1 `test_changed_secret_marks_unreadable_and_falls_back`, `test_set_without_secret_raises` ; Task 3 `test_put_without_secret_returns_503`)*
4. **Prise en compte immédiate** : une clé changée dans l'interface est utilisée par la génération suivante (Anthropic et OpenRouter) et par Jev, sans redémarrage. *(tests : Task 2)*
5. **Saisie vide ou espaces** : refusée (422), la configuration existante n'est pas effacée. *(test : Task 3, `test_put_blank_key_returns_422`)*

---

### Task 1 : Stockage chiffré et résolution des clés

**Files :**
- Create : `backend/services/api_keys.py`, `backend/alembic/versions/0006_add_app_settings.py`, `backend/tests/test_api_keys.py`
- Modify : `backend/config.py`, `backend/models.py`, `backend/requirements.txt`, `backend/tests/conftest.py`

**Interfaces :**
- Produces :
  - `services.api_keys.Provider` (dataclass figée : `id`, `label`, `env_var`) ; `PROVIDERS: tuple[Provider, ...]` ; `get_provider(provider_id: str) -> Provider | None`
  - `get_api_key(provider_id: str) -> str` (clé en vigueur, `""` si aucune)
  - `set_api_key(provider_id: str, value: str) -> None` (lève `EncryptionNotConfigured` sans `APP_SECRET_KEY` valide)
  - `delete_api_key(provider_id: str) -> None`
  - `key_status(provider_id: str) -> dict` : `{"provider", "label", "source": "interface"|"env"|"none", "masked": str | None, "unreadable": bool}`
  - `encryption_ready() -> bool` ; `mask(value: str) -> str` ; `EncryptionNotConfigured(Exception)`
  - `services.api_keys._session_factory` (remplaçable, pointé sur la base de test par `conftest.py`)
  - `models.AppSetting` (table `app_settings` : `key` String(100) PK, `value` Text, `updated_at` DateTime)
  - `settings.app_secret_key: str = ""`, `settings.admin_trust_proxy_header: bool = False`, `settings.anthropic_api_key: str = ""`

- [ ] **Step 1 : Worktree et environnement**

```bash
cd /d/2026/Projet/youtube-transcript-resume
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0='*'
git worktree add ../youtube-transcript-resume-admin -b feat/admin-api-keys
cd ../youtube-transcript-resume-admin/backend
python -m venv .venv-win
echo "cryptography==50.0.1" >> requirements.txt
.venv-win/Scripts/python -m pip install -q -r requirements-dev.txt -r requirements.txt
cp ../../youtube-transcript-resume/backend/.env .env
.venv-win/Scripts/python -m pytest -q
```

Expected : suite de `main` verte (59 tests après fusion de `feat/model-selection`).

- [ ] **Step 2 : Base de test partagée par les services** — remplacer entièrement `backend/tests/conftest.py` par :

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
from services import api_keys

# Module-scoped on purpose: shared in-memory DB via StaticPool; schema is created/dropped per test.
_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

# Les services qui ouvrent leur propre session (clés API) utilisent aussi la base de test.
api_keys._session_factory = _TestingSession


@pytest.fixture(autouse=True)
def _schema():
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture
def db_session():
    session = _TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    del app.dependency_overrides[get_db]
```

- [ ] **Step 3 : Écrire les tests qui échouent** — `backend/tests/test_api_keys.py`

```python
import pytest
from cryptography.fernet import Fernet

from models import AppSetting
from services import api_keys
from services.api_keys import EncryptionNotConfigured


@pytest.fixture
def secret(monkeypatch):
    monkeypatch.setattr(api_keys.settings, "app_secret_key", Fernet.generate_key().decode())


@pytest.fixture
def env_keys(monkeypatch):
    monkeypatch.setattr(api_keys.settings, "anthropic_api_key", "")
    monkeypatch.setattr(api_keys.settings, "openrouter_api_key", "sk-or-env-0000000000001111")
    monkeypatch.setattr(api_keys.settings, "ai_gateway_api_key", "")


def test_providers():
    assert [p.id for p in api_keys.PROVIDERS] == ["anthropic", "openrouter", "ai_gateway"]
    assert api_keys.get_provider("openrouter").env_var == "openrouter_api_key"
    assert api_keys.get_provider("nope") is None


def test_mask():
    assert api_keys.mask("sk-or-v1-abcdefghijkl1234") == "sk-or-…1234"
    assert api_keys.mask("short") == "••••"


def test_falls_back_to_env(env_keys):
    assert api_keys.get_api_key("openrouter") == "sk-or-env-0000000000001111"
    assert api_keys.get_api_key("anthropic") == ""
    assert api_keys.key_status("openrouter") == {
        "provider": "openrouter",
        "label": "OpenRouter (modèles et Jev)",
        "source": "env",
        "masked": "sk-or-…1111",
        "unreadable": False,
    }
    assert api_keys.key_status("anthropic")["source"] == "none"
    assert api_keys.key_status("anthropic")["masked"] is None


def test_set_overrides_env_and_is_encrypted(env_keys, secret, db_session):
    api_keys.set_api_key("openrouter", "sk-or-ui-9999999999992222")

    assert api_keys.get_api_key("openrouter") == "sk-or-ui-9999999999992222"
    assert api_keys.key_status("openrouter")["source"] == "interface"
    row = db_session.get(AppSetting, "api_key.openrouter")
    assert row is not None
    assert "sk-or-ui" not in row.value


def test_set_twice_replaces(env_keys, secret):
    api_keys.set_api_key("anthropic", "sk-ant-first-000000000000")
    api_keys.set_api_key("anthropic", "sk-ant-second-00000000000")
    assert api_keys.get_api_key("anthropic") == "sk-ant-second-00000000000"


def test_delete_falls_back_to_env(env_keys, secret):
    api_keys.set_api_key("openrouter", "sk-or-ui-9999999999992222")
    api_keys.delete_api_key("openrouter")
    assert api_keys.get_api_key("openrouter") == "sk-or-env-0000000000001111"
    api_keys.delete_api_key("openrouter")  # idempotent


def test_set_without_secret_raises(env_keys, monkeypatch):
    monkeypatch.setattr(api_keys.settings, "app_secret_key", "")
    assert api_keys.encryption_ready() is False
    with pytest.raises(EncryptionNotConfigured):
        api_keys.set_api_key("openrouter", "sk-or-ui-9999999999992222")


def test_invalid_secret_is_not_ready(monkeypatch):
    monkeypatch.setattr(api_keys.settings, "app_secret_key", "pas-une-cle-fernet")
    assert api_keys.encryption_ready() is False


def test_changed_secret_marks_unreadable_and_falls_back(env_keys, secret, monkeypatch):
    api_keys.set_api_key("openrouter", "sk-or-ui-9999999999992222")
    monkeypatch.setattr(api_keys.settings, "app_secret_key", Fernet.generate_key().decode())

    assert api_keys.get_api_key("openrouter") == "sk-or-env-0000000000001111"
    status = api_keys.key_status("openrouter")
    assert status["unreadable"] is True
    assert status["source"] == "env"
```

- [ ] **Step 4 : Vérifier l'échec**

Run : `.venv-win/Scripts/python -m pytest tests/test_api_keys.py -q`
Expected : FAIL — `ImportError: cannot import name 'api_keys' from 'services'` (et conftest en erreur tant que le module n'existe pas).

- [ ] **Step 5 : Configuration** — `backend/config.py`, remplacer la classe `Settings` par :

```python
class Settings(BaseSettings):
    # Clés des fournisseurs : valeurs par défaut, remplaçables depuis la page
    # Administration (services/api_keys.py).
    anthropic_api_key: str = ""
    # Jev (classement/notation) : OpenRouter prioritaire, sinon Vercel AI
    # Gateway. Aucune des deux clés = Jev désactivé.
    openrouter_api_key: str = ""
    ai_gateway_api_key: str = ""
    # Clé maître Fernet chiffrant les clés saisies dans l'administration.
    app_secret_key: str = ""
    # Docker uniquement : faire confiance à l'en-tête X-Admin-Access posé par
    # le bloc nginx d'administration (port 8080 lié à 127.0.0.1).
    admin_trust_proxy_header: bool = False
    database_url: str = "sqlite:///./yt_summaries.db"

    model_config = {"env_file": ".env"}
```

- [ ] **Step 6 : Table et migration**

Dans `backend/models.py`, ajouter à la fin :

```python
class AppSetting(Base):
    """Réglage modifiable depuis l'administration (valeurs sensibles chiffrées)."""

    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

`backend/alembic/versions/0006_add_app_settings.py` :

```python
"""add app_settings (clés API saisies dans l'administration, chiffrées)

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-27
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("app_settings"):
        op.create_table(
            "app_settings",
            sa.Column("key", sa.String(100), primary_key=True),
            sa.Column("value", sa.Text(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("app_settings")
```

- [ ] **Step 7 : Service** — `backend/services/api_keys.py`

```python
"""Clés API des fournisseurs.

Clé en vigueur = clé saisie dans l'administration (chiffrée en base avec
APP_SECRET_KEY), sinon variable du .env, sinon "".
"""
from dataclasses import dataclass

from cryptography.fernet import Fernet, InvalidToken

from config import settings
from database import SessionLocal
from models import AppSetting


@dataclass(frozen=True)
class Provider:
    id: str
    label: str
    env_var: str  # attribut de Settings (= variable du .env en minuscules)


PROVIDERS: tuple[Provider, ...] = (
    Provider("anthropic", "Anthropic (Claude en direct)", "anthropic_api_key"),
    Provider("openrouter", "OpenRouter (modèles et Jev)", "openrouter_api_key"),
    Provider("ai_gateway", "Vercel AI Gateway (Jev, secours)", "ai_gateway_api_key"),
)
_BY_ID = {p.id: p for p in PROVIDERS}

# Remplacé par la base de test dans tests/conftest.py.
_session_factory = SessionLocal


class EncryptionNotConfigured(Exception):
    """APP_SECRET_KEY absente ou invalide : impossible d'enregistrer une clé."""


def get_provider(provider_id: str) -> Provider | None:
    return _BY_ID.get(provider_id)


def _fernet() -> Fernet | None:
    if not settings.app_secret_key:
        return None
    try:
        return Fernet(settings.app_secret_key.encode())
    except ValueError:
        return None


def encryption_ready() -> bool:
    return _fernet() is not None


def _row_key(provider: Provider) -> str:
    return f"api_key.{provider.id}"


def _stored(provider: Provider) -> tuple[str | None, bool]:
    """(clé saisie déchiffrée ou None, clé stockée mais illisible)."""
    with _session_factory() as db:
        row = db.get(AppSetting, _row_key(provider))
        token = row.value if row else None
    if token is None:
        return None, False
    fernet = _fernet()
    if fernet is None:
        return None, True
    try:
        return fernet.decrypt(token.encode()).decode(), False
    except InvalidToken:
        return None, True


def get_api_key(provider_id: str) -> str:
    provider = _BY_ID[provider_id]
    stored, _ = _stored(provider)
    return stored or getattr(settings, provider.env_var)


def set_api_key(provider_id: str, value: str) -> None:
    provider = _BY_ID[provider_id]
    fernet = _fernet()
    if fernet is None:
        raise EncryptionNotConfigured()
    token = fernet.encrypt(value.encode()).decode()
    with _session_factory() as db:
        row = db.get(AppSetting, _row_key(provider))
        if row is None:
            db.add(AppSetting(key=_row_key(provider), value=token))
        else:
            row.value = token
        db.commit()


def delete_api_key(provider_id: str) -> None:
    provider = _BY_ID[provider_id]
    with _session_factory() as db:
        row = db.get(AppSetting, _row_key(provider))
        if row is not None:
            db.delete(row)
            db.commit()


def mask(value: str) -> str:
    return f"{value[:6]}…{value[-4:]}" if len(value) > 12 else "••••"


def key_status(provider_id: str) -> dict:
    provider = _BY_ID[provider_id]
    stored, unreadable = _stored(provider)
    env_value = getattr(settings, provider.env_var)
    if stored:
        source, value = "interface", stored
    elif env_value:
        source, value = "env", env_value
    else:
        source, value = "none", ""
    return {
        "provider": provider.id,
        "label": provider.label,
        "source": source,
        "masked": mask(value) if value else None,
        "unreadable": unreadable,
    }
```

- [ ] **Step 8 : Vérifier le passage des tests**

Run : `.venv-win/Scripts/python -m pytest -q`
Expected : toute la suite passe (59 + 9 nouveaux = 68).

- [ ] **Step 9 : Commit**

```bash
git add backend/services/api_keys.py backend/alembic/versions/0006_add_app_settings.py backend/tests/test_api_keys.py backend/tests/conftest.py backend/config.py backend/models.py backend/requirements.txt
git commit -m "feat: stockage chiffré des clés API et résolution interface > .env

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2 : Les consommateurs utilisent la clé en vigueur

**Files :**
- Modify : `backend/services/llm_models.py`, `backend/services/evaluator.py`, `backend/services/summarizer.py`, `backend/tests/test_summarizer_models.py`, `backend/tests/test_models.py`, `backend/tests/test_jev.py`
- Create : `backend/tests/test_api_keys_consumers.py`

**Interfaces :**
- Consumes : `get_api_key(provider_id)` (Task 1).
- Produces : `services.summarizer._anthropic_client() -> anthropic.AsyncAnthropic` (client pour la clé en vigueur, recréé si elle change). Plus aucun module ne lit `settings.*_api_key` directement, sauf `services/api_keys.py`.

- [ ] **Step 1 : Écrire les tests qui échouent** — `backend/tests/test_api_keys_consumers.py`

```python
import json

import httpx
import pytest
from cryptography.fernet import Fernet

from services import api_keys, evaluator, llm_models, summarizer


@pytest.fixture
def secret(monkeypatch):
    monkeypatch.setattr(api_keys.settings, "app_secret_key", Fernet.generate_key().decode())
    monkeypatch.setattr(api_keys.settings, "anthropic_api_key", "sk-ant-env-000000000000")
    monkeypatch.setattr(api_keys.settings, "openrouter_api_key", "")
    monkeypatch.setattr(api_keys.settings, "ai_gateway_api_key", "")


def test_model_availability_follows_ui_key(secret):
    gemini = llm_models.get_model("google/gemini-3.1-flash-lite")
    assert llm_models.is_available(gemini) is False
    api_keys.set_api_key("openrouter", "sk-or-ui-000000000000")
    assert llm_models.is_available(gemini) is True


def test_jev_uses_ui_openrouter_key(secret):
    assert evaluator.is_enabled() is False
    api_keys.set_api_key("openrouter", "sk-or-ui-000000000000")
    assert evaluator._provider() == (
        evaluator.OPENROUTER_URL, evaluator.OPENROUTER_MODEL, "sk-or-ui-000000000000"
    )


def test_anthropic_client_follows_key_change(secret):
    first = summarizer._anthropic_client()
    assert first.api_key == "sk-ant-env-000000000000"
    assert summarizer._anthropic_client() is first  # réutilisé tant que la clé ne change pas
    api_keys.set_api_key("anthropic", "sk-ant-ui-111111111111")
    second = summarizer._anthropic_client()
    assert second.api_key == "sk-ant-ui-111111111111"


@pytest.mark.anyio
async def test_openrouter_generation_uses_ui_key(secret, monkeypatch):
    api_keys.set_api_key("openrouter", "sk-or-ui-000000000000")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        return httpx.Response(200, json={
            "choices": [{"message": {"content": json.dumps({"summary_short": "c", "summary_long": "l"})}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "cost": 0.0001},
        })

    monkeypatch.setattr(summarizer, "_openrouter_transport", httpx.MockTransport(handler))
    await summarizer.generate_summary("t", "T", model="google/gemini-3.1-flash-lite")
    assert seen["auth"] == "Bearer sk-or-ui-000000000000"
```

- [ ] **Step 2 : Vérifier l'échec**

Run : `.venv-win/Scripts/python -m pytest tests/test_api_keys_consumers.py -q`
Expected : FAIL — `AttributeError: module 'services.summarizer' has no attribute '_anthropic_client'` et disponibilité/Jev qui ignorent la clé saisie.

- [ ] **Step 3 : Catalogue** — `backend/services/llm_models.py` : remplacer `from config import settings` par `from services.api_keys import get_api_key` et `is_available` par :

```python
def is_available(model: LLMModel) -> bool:
    return bool(get_api_key("openrouter" if model.provider == "openrouter" else "anthropic"))
```

- [ ] **Step 4 : Jev** — `backend/services/evaluator.py` : remplacer `from config import settings` par `from services.api_keys import get_api_key` et `_provider` par :

```python
def _provider() -> tuple[str, str, str] | None:
    """(url, modèle, clé) du fournisseur configuré, OpenRouter en priorité."""
    openrouter_key = get_api_key("openrouter")
    if openrouter_key:
        return OPENROUTER_URL, OPENROUTER_MODEL, openrouter_key
    gateway_key = get_api_key("ai_gateway")
    if gateway_key:
        return VERCEL_URL, VERCEL_MODEL, gateway_key
    return None
```

- [ ] **Step 5 : Génération** — `backend/services/summarizer.py` :
  - remplacer `from config import settings` par `from services.api_keys import get_api_key` ;
  - remplacer la ligne `_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)` par :

```python
_anthropic_clients: dict[str, anthropic.AsyncAnthropic] = {}


def _anthropic_client() -> anthropic.AsyncAnthropic:
    """Client Anthropic pour la clé en vigueur (recréé si la clé change)."""
    key = get_api_key("anthropic")
    client = _anthropic_clients.get(key)
    if client is None:
        _anthropic_clients.clear()
        client = _anthropic_clients[key] = anthropic.AsyncAnthropic(api_key=key)
    return client
```

  - dans `_call_anthropic`, remplacer `_client.messages.stream(` par `_anthropic_client().messages.stream(` ;
  - dans `_call_openrouter`, remplacer `f"Bearer {settings.openrouter_api_key}"` par `f"Bearer {get_api_key('openrouter')}"`.

- [ ] **Step 6 : Adapter les tests existants**
  - `tests/test_summarizer_models.py` : les deux `monkeypatch.setattr(summarizer._client.messages, "stream", X)` deviennent

```python
    fake_client = SimpleNamespace(messages=SimpleNamespace(stream=X))
    monkeypatch.setattr(summarizer, "_anthropic_client", lambda: fake_client)
```

    (avec `from types import SimpleNamespace` en tête), et chaque `monkeypatch.setattr(summarizer.settings, …)` / `monkeypatch.setattr(llm_models.settings, …)` devient `monkeypatch.setattr(api_keys.settings, …)` (`from services import api_keys`) — c'est le même objet `settings`, seul le module qui l'expose change.
  - `tests/test_models.py` et `tests/test_jev.py` : même remplacement de `llm_models.settings` / `evaluator.settings` par `api_keys.settings`.

- [ ] **Step 7 : Vérifier**

Run : `.venv-win/Scripts/python -m pytest -q` puis `grep -rn "settings\.\(anthropic\|openrouter\|ai_gateway\)_api_key" services routers`
Expected : 72 tests verts (68 + 4) ; le grep ne renvoie aucune ligne (seul `services/api_keys.py` lit les clés, via `getattr(settings, provider.env_var)`).

- [ ] **Step 8 : Commit**

```bash
git add backend/services backend/tests
git commit -m "feat: génération, catalogue et Jev utilisent la clé API en vigueur

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3 : API d'administration réservée à la machine locale

**Files :**
- Create : `backend/routers/admin.py`, `backend/services/key_check.py`, `backend/tests/test_admin.py`
- Modify : `backend/schemas.py`, `backend/main.py`

**Interfaces :**
- Consumes : `PROVIDERS`, `get_provider`, `get_api_key`, `set_api_key`, `delete_api_key`, `key_status`, `encryption_ready`, `EncryptionNotConfigured` (Task 1) ; `settings.admin_trust_proxy_header`.
- Produces (préfixe `/admin-api`, toutes protégées par `require_local_admin`) :
  - `GET /admin-api/keys/` → `AdminKeysOut {encryption_ready: bool, keys: list[ApiKeyStatus]}`
  - `PUT /admin-api/keys/{provider}` corps `ApiKeyIn {value: str}` → `ApiKeyStatus` ; 404 fournisseur inconnu, 422 clé vide, 503 chiffrement non configuré
  - `DELETE /admin-api/keys/{provider}` → `ApiKeyStatus`
  - `POST /admin-api/keys/{provider}/test` → `ApiKeyTestResult {ok: bool, message: str}`
  - `ApiKeyStatus {provider, label, source, masked: str | None, unreadable: bool}`
  - `routers.admin.require_local_admin(request)` ; `services.key_check.check_key(provider_id, key) -> tuple[bool, str]` ; `services.key_check._transport`

- [ ] **Step 1 : Écrire les tests qui échouent** — `backend/tests/test_admin.py`

```python
import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from starlette.requests import Request

from main import app
from routers.admin import require_local_admin
from services import api_keys, key_check

_KEY = "sk-or-ui-abcdefghijklmnop4321"


def _request(host: str, headers: dict[str, str] | None = None) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({"type": "http", "client": (host, 50000), "headers": raw})


@pytest.fixture
def trust_proxy(monkeypatch):
    monkeypatch.setattr(api_keys.settings, "admin_trust_proxy_header", True)


@pytest.fixture
def no_trust_proxy(monkeypatch):
    monkeypatch.setattr(api_keys.settings, "admin_trust_proxy_header", False)


@pytest.fixture
def admin(client):
    app.dependency_overrides[require_local_admin] = lambda: None
    yield client
    del app.dependency_overrides[require_local_admin]


@pytest.fixture
def secret(monkeypatch):
    monkeypatch.setattr(api_keys.settings, "app_secret_key", Fernet.generate_key().decode())
    monkeypatch.setattr(api_keys.settings, "openrouter_api_key", "")


# ── Accès ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("host", ["127.0.0.1", "::1"])
def test_require_local_admin_accepts_loopback(host, no_trust_proxy):
    require_local_admin(_request(host))


def test_require_local_admin_rejects_network_client(no_trust_proxy):
    with pytest.raises(HTTPException) as exc:
        require_local_admin(_request("192.168.1.20"))
    assert exc.value.status_code == 403


def test_require_local_admin_ignores_header_without_trust(no_trust_proxy):
    with pytest.raises(HTTPException):
        require_local_admin(_request("192.168.1.20", {"X-Admin-Access": "local"}))


def test_require_local_admin_accepts_proxy_header_when_trusted(trust_proxy):
    require_local_admin(_request("172.18.0.3", {"X-Admin-Access": "local"}))


def test_require_local_admin_rejects_other_header_value(trust_proxy):
    with pytest.raises(HTTPException):
        require_local_admin(_request("172.18.0.3", {"X-Admin-Access": "yes"}))


def test_admin_routes_forbidden_from_test_client(client, no_trust_proxy):
    r = client.get("/admin-api/keys/")
    assert r.status_code == 403
    assert "uniquement depuis cette machine" in r.json()["detail"]


# ── Clés ─────────────────────────────────────────────────────────────────────

def test_list_keys(admin, secret):
    body = admin.get("/admin-api/keys/").json()
    assert body["encryption_ready"] is True
    assert [k["provider"] for k in body["keys"]] == ["anthropic", "openrouter", "ai_gateway"]


def test_put_key_never_returns_plaintext(admin, secret):
    r = admin.put("/admin-api/keys/openrouter", json={"value": f"  {_KEY}  "})
    assert r.status_code == 200
    assert r.json() == {
        "provider": "openrouter",
        "label": "OpenRouter (modèles et Jev)",
        "source": "interface",
        "masked": "sk-or-…4321",
        "unreadable": False,
    }
    assert _KEY not in r.text
    assert _KEY not in admin.get("/admin-api/keys/").text
    assert api_keys.get_api_key("openrouter") == _KEY  # espaces retirés


def test_put_blank_key_returns_422(admin, secret):
    admin.put("/admin-api/keys/openrouter", json={"value": _KEY})
    r = admin.put("/admin-api/keys/openrouter", json={"value": "   "})
    assert r.status_code == 422
    assert api_keys.get_api_key("openrouter") == _KEY


def test_put_unknown_provider_returns_404(admin, secret):
    assert admin.put("/admin-api/keys/nope", json={"value": _KEY}).status_code == 404


def test_put_without_secret_returns_503(admin, monkeypatch):
    monkeypatch.setattr(api_keys.settings, "app_secret_key", "")
    r = admin.put("/admin-api/keys/openrouter", json={"value": _KEY})
    assert r.status_code == 503
    assert "APP_SECRET_KEY" in r.json()["detail"]


def test_delete_key_falls_back_to_env(admin, secret, monkeypatch):
    monkeypatch.setattr(api_keys.settings, "openrouter_api_key", "sk-or-env-000000009999")
    admin.put("/admin-api/keys/openrouter", json={"value": _KEY})
    r = admin.delete("/admin-api/keys/openrouter")
    assert r.status_code == 200
    assert r.json()["source"] == "env"
    assert r.json()["masked"] == "sk-or-…9999"


# ── Test d'une clé ───────────────────────────────────────────────────────────

def _provider_replies(monkeypatch, status: int, seen: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["headers"] = dict(request.headers)
        return httpx.Response(status, json={})

    monkeypatch.setattr(key_check, "_transport", httpx.MockTransport(handler))


def test_key_test_ok(admin, secret, monkeypatch):
    admin.put("/admin-api/keys/openrouter", json={"value": _KEY})
    seen = {}
    _provider_replies(monkeypatch, 200, seen)
    r = admin.post("/admin-api/keys/openrouter/test")
    assert r.json() == {"ok": True, "message": "Clé valide"}
    assert seen["url"] == "https://openrouter.ai/api/v1/key"
    assert seen["headers"]["authorization"] == f"Bearer {_KEY}"


def test_key_test_rejected(admin, secret, monkeypatch):
    admin.put("/admin-api/keys/openrouter", json={"value": _KEY})
    _provider_replies(monkeypatch, 401, {})
    assert admin.post("/admin-api/keys/openrouter/test").json() == {
        "ok": False, "message": "Clé refusée par le fournisseur",
    }


def test_key_test_anthropic_headers(admin, secret, monkeypatch):
    monkeypatch.setattr(api_keys.settings, "anthropic_api_key", "sk-ant-env-000000000000")
    seen = {}
    _provider_replies(monkeypatch, 200, seen)
    admin.post("/admin-api/keys/anthropic/test")
    assert seen["url"] == "https://api.anthropic.com/v1/models"
    assert seen["headers"]["x-api-key"] == "sk-ant-env-000000000000"
    assert seen["headers"]["anthropic-version"] == "2023-06-01"


def test_key_test_without_key(admin, secret, monkeypatch):
    monkeypatch.setattr(api_keys.settings, "ai_gateway_api_key", "")
    assert admin.post("/admin-api/keys/ai_gateway/test").json() == {
        "ok": False, "message": "Aucune clé configurée",
    }


def test_key_test_network_error_does_not_leak_key(admin, secret, monkeypatch):
    admin.put("/admin-api/keys/openrouter", json={"value": _KEY})

    def handler(request):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(key_check, "_transport", httpx.MockTransport(handler))
    body = admin.post("/admin-api/keys/openrouter/test").json()
    assert body["ok"] is False
    assert body["message"].startswith("Fournisseur injoignable")
    assert _KEY not in body["message"]
```

- [ ] **Step 2 : Vérifier l'échec**

Run : `.venv-win/Scripts/python -m pytest tests/test_admin.py -q`
Expected : FAIL — `ModuleNotFoundError: No module named 'routers.admin'`.

- [ ] **Step 3 : Schémas** — dans `backend/schemas.py`, ajouter :

```python
# ── Administration ───────────────────────────────────────────────────────────

class ApiKeyStatus(BaseModel):
    provider: str
    label: str
    source: str  # "interface" | "env" | "none"
    masked: Optional[str]
    unreadable: bool


class AdminKeysOut(BaseModel):
    encryption_ready: bool
    keys: list[ApiKeyStatus]


class ApiKeyIn(BaseModel):
    value: str

    @field_validator("value")
    @classmethod
    def strip_and_require(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("La clé ne peut pas être vide")
        return v


class ApiKeyTestResult(BaseModel):
    ok: bool
    message: str
```

- [ ] **Step 4 : Vérification d'une clé** — `backend/services/key_check.py`

```python
"""Vérifie une clé API par un appel gratuit au fournisseur (liste de modèles
ou informations sur la clé), sans rien générer."""
from collections.abc import Callable

import httpx

# Transport httpx injectable pour les tests.
_transport: httpx.AsyncBaseTransport | None = None

_CHECKS: dict[str, tuple[str, Callable[[str], dict[str, str]]]] = {
    "anthropic": (
        "https://api.anthropic.com/v1/models",
        lambda key: {"x-api-key": key, "anthropic-version": "2023-06-01"},
    ),
    "openrouter": (
        "https://openrouter.ai/api/v1/key",
        lambda key: {"Authorization": f"Bearer {key}"},
    ),
    "ai_gateway": (
        "https://ai-gateway.vercel.sh/v1/models",
        lambda key: {"Authorization": f"Bearer {key}"},
    ),
}


async def check_key(provider_id: str, key: str) -> tuple[bool, str]:
    if not key:
        return False, "Aucune clé configurée"
    url, headers = _CHECKS[provider_id]
    try:
        async with httpx.AsyncClient(timeout=15, transport=_transport) as client:
            resp = await client.get(url, headers=headers(key))
    except httpx.HTTPError as exc:
        return False, f"Fournisseur injoignable : {type(exc).__name__}"
    if resp.status_code == 200:
        return True, "Clé valide"
    if resp.status_code in (401, 403):
        return False, "Clé refusée par le fournisseur"
    return False, f"Réponse inattendue du fournisseur ({resp.status_code})"
```

(Le message d'erreur réseau ne reprend que le type d'exception : le texte d'une exception httpx peut contenir l'URL et, par prudence, on n'y expose rien d'autre.)

- [ ] **Step 5 : Routeur** — `backend/routers/admin.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Request

from config import settings
from schemas import AdminKeysOut, ApiKeyIn, ApiKeyStatus, ApiKeyTestResult
from services.api_keys import (
    PROVIDERS,
    EncryptionNotConfigured,
    delete_api_key,
    encryption_ready,
    get_api_key,
    get_provider,
    key_status,
    set_api_key,
)
from services.key_check import check_key

ADMIN_ACCESS_HEADER = "x-admin-access"
_LOOPBACK = {"127.0.0.1", "::1"}


def require_local_admin(request: Request) -> None:
    """N'autorise que la machine locale : client loopback (développement) ou,
    sous Docker, l'en-tête posé par le bloc nginx du port 127.0.0.1:8080."""
    host = request.client.host if request.client else ""
    if host in _LOOPBACK:
        return
    if settings.admin_trust_proxy_header and request.headers.get(ADMIN_ACCESS_HEADER) == "local":
        return
    raise HTTPException(
        status_code=403,
        detail="Administration accessible uniquement depuis cette machine",
    )


router = APIRouter(dependencies=[Depends(require_local_admin)])


def _require_provider(provider: str) -> str:
    if get_provider(provider) is None:
        raise HTTPException(status_code=404, detail=f"Fournisseur inconnu : {provider}")
    return provider


@router.get("/keys/", response_model=AdminKeysOut)
def list_keys():
    return AdminKeysOut(
        encryption_ready=encryption_ready(),
        keys=[ApiKeyStatus(**key_status(p.id)) for p in PROVIDERS],
    )


@router.put("/keys/{provider}", response_model=ApiKeyStatus)
def save_key(provider: str, payload: ApiKeyIn):
    _require_provider(provider)
    try:
        set_api_key(provider, payload.value)
    except EncryptionNotConfigured:
        raise HTTPException(
            status_code=503,
            detail="Chiffrement non configuré : ajoutez APP_SECRET_KEY dans backend/.env",
        )
    return ApiKeyStatus(**key_status(provider))


@router.delete("/keys/{provider}", response_model=ApiKeyStatus)
def remove_key(provider: str):
    _require_provider(provider)
    delete_api_key(provider)
    return ApiKeyStatus(**key_status(provider))


@router.post("/keys/{provider}/test", response_model=ApiKeyTestResult)
async def test_key(provider: str):
    _require_provider(provider)
    ok, message = await check_key(provider, get_api_key(provider))
    return ApiKeyTestResult(ok=ok, message=message)
```

Dans `backend/main.py` : ajouter `admin` à l'import `from routers import …` et, après les autres `include_router` :

```python
app.include_router(admin.router, prefix="/admin-api", tags=["admin"])
```

- [ ] **Step 6 : Vérifier le passage des tests**

Run : `.venv-win/Scripts/python -m pytest -q`
Expected : toute la suite passe (72 + 18 nouveaux = 90).

- [ ] **Step 7 : Commit**

```bash
git add backend/routers/admin.py backend/services/key_check.py backend/tests/test_admin.py backend/schemas.py backend/main.py
git commit -m "feat: API d'administration des clés, réservée à la machine locale

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4 : Page « Administration »

**Files :**
- Create : `frontend/src/api/admin.ts`, `frontend/src/pages/AdminPage.tsx`, `frontend/src/pages/AdminPage.module.css`
- Modify : `frontend/src/App.tsx`, `frontend/src/components/Layout.tsx`, `frontend/vite.config.ts`

**Interfaces :**
- Consumes : les routes `/admin-api/…` de Task 3 (403 hors machine locale).

Pas de framework de test frontend : vérification par `npm run build`, `npx eslint` sur les fichiers touchés, puis contrôle navigateur par le contrôleur.

- [ ] **Step 1 : Client API** — `frontend/src/api/admin.ts`

```ts
import api from "./client";

export interface ApiKeyStatus {
  provider: "anthropic" | "openrouter" | "ai_gateway";
  label: string;
  source: "interface" | "env" | "none";
  masked: string | null;
  unreadable: boolean;
}

export interface AdminKeys {
  encryption_ready: boolean;
  keys: ApiKeyStatus[];
}

export interface ApiKeyTestResult {
  ok: boolean;
  message: string;
}

export const getAdminKeys = () => api.get<AdminKeys>("/admin-api/keys/").then((r) => r.data);

export const saveApiKey = (provider: string, value: string) =>
  api.put<ApiKeyStatus>(`/admin-api/keys/${provider}`, { value }).then((r) => r.data);

export const deleteApiKey = (provider: string) =>
  api.delete<ApiKeyStatus>(`/admin-api/keys/${provider}`).then((r) => r.data);

export const testApiKey = (provider: string) =>
  api.post<ApiKeyTestResult>(`/admin-api/keys/${provider}/test`).then((r) => r.data);
```

- [ ] **Step 2 : Page** — `frontend/src/pages/AdminPage.tsx`

```tsx
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { deleteApiKey, getAdminKeys, saveApiKey, testApiKey } from "../api/admin";
import type { ApiKeyStatus, ApiKeyTestResult } from "../api/admin";
import { useConfirm } from "../components/ConfirmDialog";
import styles from "./AdminPage.module.css";

const SOURCE_LABEL: Record<ApiKeyStatus["source"], string> = {
  interface: "Saisie ici",
  env: "Fichier .env",
  none: "Non configurée",
};

const errorDetail = (err: unknown) =>
  (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;

function KeyRow({ status, canSave }: { status: ApiKeyStatus; canSave: boolean }) {
  const queryClient = useQueryClient();
  const confirm = useConfirm();
  const [value, setValue] = useState("");
  const [error, setError] = useState("");
  const [testResult, setTestResult] = useState<ApiKeyTestResult | null>(null);

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["admin-keys"] });
    queryClient.invalidateQueries({ queryKey: ["models"] });
  };

  const save = useMutation({
    mutationFn: () => saveApiKey(status.provider, value),
    onSuccess: () => { setValue(""); setError(""); setTestResult(null); refresh(); },
    onError: (err) => {
      const detail = errorDetail(err);
      setError(typeof detail === "string" ? detail : "Enregistrement impossible.");
    },
  });
  const remove = useMutation({
    mutationFn: () => deleteApiKey(status.provider),
    onSuccess: () => { setTestResult(null); refresh(); },
  });
  const test = useMutation({
    mutationFn: () => testApiKey(status.provider),
    onSuccess: setTestResult,
  });

  return (
    <li className={styles.row}>
      <div className={styles.rowHead}>
        <span className={styles.label}>{status.label}</span>
        <span className={`${styles.source} ${styles[status.source]}`}>{SOURCE_LABEL[status.source]}</span>
        {status.masked && <code className={styles.masked}>{status.masked}</code>}
      </div>
      {status.unreadable && (
        <p className={styles.warning}>
          La clé saisie ici est illisible (APP_SECRET_KEY a changé) : elle est ignorée. Saisissez-la de nouveau.
        </p>
      )}
      <form
        className={styles.form}
        onSubmit={(e) => { e.preventDefault(); if (value.trim()) save.mutate(); }}
      >
        <input
          type="password"
          autoComplete="off"
          name={`key-${status.provider}`}
          className={styles.input}
          placeholder={status.source === "none" ? "Coller la clé API" : "Nouvelle clé (remplace l'actuelle)"}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={!canSave || save.isPending}
        />
        <button type="submit" className={`${styles.btnPrimary} u-pill-btn`} disabled={!canSave || !value.trim() || save.isPending}>
          Enregistrer
        </button>
        <button type="button" className={styles.btnGhost} onClick={() => test.mutate()} disabled={status.source === "none" || test.isPending}>
          {test.isPending ? "Test…" : "Tester"}
        </button>
        {status.source === "interface" && (
          <button
            type="button"
            className={styles.btnDanger}
            disabled={remove.isPending}
            onClick={async () => {
              if (await confirm(`Supprimer la clé saisie pour ${status.label} ? La clé du fichier .env sera utilisée si elle existe.`, { confirmLabel: "Supprimer", danger: true })) {
                remove.mutate();
              }
            }}
          >
            Supprimer
          </button>
        )}
      </form>
      {error && <p className={styles.error}>{error}</p>}
      {testResult && (
        <p className={testResult.ok ? styles.ok : styles.error}>{testResult.message}</p>
      )}
    </li>
  );
}

export default function AdminPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["admin-keys"],
    queryFn: getAdminKeys,
    retry: false,
  });

  const forbidden = axios.isAxiosError(error) && error.response?.status === 403;

  return (
    <div className={styles.wrap}>
      <h1 className={`${styles.title} u-lime-title`}>Administration</h1>

      {isLoading && <p className={styles.hint}>Chargement…</p>}

      {forbidden && (
        <section className={`${styles.card} u-glow-surface`}>
          <h2>Accès restreint</h2>
          <p className={styles.hint}>
            L'administration n'est accessible que depuis la machine qui héberge l'application :
            ouvrez <code>http://localhost:8080/admin</code> (Docker) ou <code>http://localhost:5173/admin</code> (développement).
          </p>
        </section>
      )}

      {error && !forbidden && <p className={styles.error}>Impossible de charger les clés.</p>}

      {data && (
        <section className={`${styles.card} u-glow-surface`}>
          <h2>Clés API</h2>
          {!data.encryption_ready && (
            <p className={styles.warning}>
              Chiffrement non configuré : ajoutez <code>APP_SECRET_KEY</code> dans <code>backend/.env</code> pour
              enregistrer des clés ici. En attendant, les clés du fichier .env restent utilisées.
            </p>
          )}
          <p className={styles.hint}>
            Une clé saisie ici remplace celle du fichier .env et s'applique immédiatement. Elle est stockée chiffrée
            et n'est jamais réaffichée en entier. Jev utilise la clé OpenRouter (à défaut, Vercel AI Gateway).
          </p>
          <ul className={styles.list}>
            {data.keys.map((k) => (
              <KeyRow key={k.provider} status={k} canSave={data.encryption_ready} />
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
```

- [ ] **Step 3 : Styles** — `frontend/src/pages/AdminPage.module.css`

```css
.wrap {
  max-width: 760px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
  animation: fadeUp .35s ease;
}

.title {
  font-size: 1.5rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  text-align: center;
}

.card {
  padding: 22px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card h2 {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text3);
}

.hint { font-size: 0.85rem; color: var(--text2); line-height: 1.5; }
.hint code, .warning code { font-family: var(--font-mono); font-size: 0.8rem; }

.list { list-style: none; display: flex; flex-direction: column; gap: 14px; }

.row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg3);
}

.rowHead { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.label { font-weight: 600; color: var(--text); flex: 1; min-width: 180px; }

.source {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid var(--border2);
  color: var(--text2);
}
.interface { color: var(--accent); border-color: var(--accent); }
.none { color: var(--danger); border-color: var(--danger); }
.env { color: var(--text2); }

.masked { font-family: var(--font-mono); font-size: 0.78rem; color: var(--text2); }

.form { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }

.input {
  flex: 1;
  min-width: 220px;
  padding: 8px 12px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  font-size: 0.85rem;
  outline: none;
}
.input:focus { border-color: var(--accent); }

.btnPrimary { font-size: 0.85rem; }

.btnGhost, .btnDanger {
  padding: 8px 14px;
  background: transparent;
  border: 1px solid var(--border2);
  border-radius: var(--radius-sm);
  color: var(--text3);
  font-size: 0.8rem;
}
.btnGhost:hover { border-color: var(--accent); color: var(--text); }
.btnDanger:hover { border-color: var(--danger); color: var(--danger); }

.ok { font-size: 0.8rem; color: var(--accent); }
.error { font-size: 0.8rem; color: var(--danger); }

.warning {
  font-size: 0.82rem;
  color: var(--danger);
  background: var(--danger-dim);
  border: 1px solid rgba(255,68,102,.2);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
}
```

- [ ] **Step 4 : Route, menu et proxy**
  - `frontend/src/App.tsx` : `import AdminPage from "./pages/AdminPage";` et, après la route `/prompts`, `<Route path="/admin" element={<AdminPage />} />`.
  - `frontend/src/components/Layout.tsx` : après le `NavLink` « Prompts », ajouter

```tsx
          <NavLink to="/admin" className={({ isActive }) => isActive ? styles.active : ""}>
            Admin
          </NavLink>
```

    (reprendre exactement la structure des `NavLink` voisins, y compris le contenu entre les balises).
  - `frontend/vite.config.ts` : dans la clé du proxy, ajouter `admin-api` : `'^/(summaries|themes|search|prompts|stats|models|admin-api)/'`.

- [ ] **Step 5 : Vérifier**

```bash
cd frontend
npm ci
npm run build
npx eslint src/api/admin.ts src/pages/AdminPage.tsx src/App.tsx src/components/Layout.tsx
```

Expected : build OK ; ESLint sans nouveau problème (le seul problème connu du projet est dans `NewSummaryPage.tsx`, non touché ici).

- [ ] **Step 6 : Commit**

```bash
git add frontend/src frontend/vite.config.ts
git commit -m "feat: page Administration des clés API

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5 : Accès local sous Docker et documentation

**Files :**
- Modify : `frontend/nginx.conf`, `docker-compose.yml`, `backend/.env.example`, `CLAUDE.md`

- [ ] **Step 1 : nginx** — remplacer entièrement `frontend/nginx.conf` par :

```nginx
# Port 80 : l'application, ouverte au réseau. L'administration y est refusée.
server {
    listen 80;

    root /usr/share/nginx/html;
    index index.html;

    # /health is hit bare (no trailing slash) by Docker/curl checks.
    location = /health {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;
    }

    # Administration des clés : uniquement via le port 8080 (lié à 127.0.0.1).
    location /admin-api/ {
        return 403;
    }

    # Proxy API calls to the backend. The frontend always calls these with a
    # trailing slash or a sub-path (/themes/, /prompts/, /summaries/2, ...),
    # so requiring a "/" after the prefix lets the bare client-side routes
    # /themes and /prompts fall through to the SPA (index.html) on refresh
    # or deep-link instead of returning raw backend JSON.
    location ~ ^/(summaries|themes|search|prompts|stats|models)/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        # Un client ne doit jamais pouvoir se faire passer pour l'administration.
        proxy_set_header X-Admin-Access "";
        proxy_read_timeout 310s;
    }

    # SPA routing (catch-all, lowest precedence)
    location / {
        try_files $uri $uri/ /index.html;
    }
}

# Port 8080 : même application + administration. docker-compose ne publie ce
# port que sur 127.0.0.1 : il n'est joignable que depuis la machine hôte.
server {
    listen 8080;

    root /usr/share/nginx/html;
    index index.html;

    location = /health {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;
    }

    location /admin-api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        # Écrase toute valeur envoyée par le client.
        proxy_set_header X-Admin-Access local;
        proxy_read_timeout 60s;
    }

    location ~ ^/(summaries|themes|search|prompts|stats|models)/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Admin-Access "";
        proxy_read_timeout 310s;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **Step 2 : Compose** — dans `docker-compose.yml` :
  - service `backend`, sous `environment:` (après `DATABASE_URL`) : `ADMIN_TRUST_PROXY_HEADER: "true"` ;
  - service `frontend`, `ports:` devient

```yaml
    ports:
      - "80:80"
      - "127.0.0.1:8080:8080"   # administration : machine hôte uniquement
```

- [ ] **Step 3 : Documentation**
  - `backend/.env.example` : remplacer le contenu par

```
# Clés des fournisseurs (facultatives : elles peuvent aussi être saisies dans
# la page Administration, qui a priorité sur ce fichier).
ANTHROPIC_API_KEY=
OPENROUTER_API_KEY=
AI_GATEWAY_API_KEY=
# Clé maître chiffrant les clés saisies dans l'Administration. Générer avec :
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
APP_SECRET_KEY=
DATABASE_URL=sqlite:///./yt_summaries.db
```

  - `CLAUDE.md`, section « Variables d'environnement » : remplacer le tableau par

```markdown
| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Clé Anthropic (facultative si saisie dans l'Administration) |
| `OPENROUTER_API_KEY` | Clé OpenRouter : modèles non-Claude et Jev (facultative si saisie dans l'Administration) |
| `AI_GATEWAY_API_KEY` | Clé Vercel AI Gateway, secours pour Jev (facultative) |
| `APP_SECRET_KEY` | Clé maître Fernet chiffrant les clés saisies dans l'Administration |
| `DATABASE_URL` | défaut : `sqlite:///./yt_summaries.db` |

Les clés peuvent être gérées dans la page **Administration**, accessible uniquement depuis la machine hôte : `http://localhost:8080/admin` (Docker, port lié à 127.0.0.1) ou `http://localhost:5173/admin` (dev). Une clé saisie là a priorité sur le `.env`.
```

- [ ] **Step 4 : Vérifier la configuration**

```bash
docker run --rm --add-host backend:127.0.0.1 -v "$(pwd -W)/frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro" nginx:alpine nginx -t
docker compose config --quiet && echo "compose OK"
```

Expected : `nginx: configuration file /etc/nginx/nginx.conf test is successful` puis `compose OK`.

- [ ] **Step 5 : Commit**

```bash
git add frontend/nginx.conf docker-compose.yml backend/.env.example CLAUDE.md
git commit -m "feat: administration joignable seulement via 127.0.0.1:8080 sous Docker, documentation

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6 : Livraison (après accord de l'utilisateur)

**Files :** aucun fichier de code.

- [ ] **Step 1 : Revue de la branche** (skill `superpowers:requesting-code-review`), corrections des points confirmés.

- [ ] **Step 2 : `APP_SECRET_KEY`** — avec l'accord de l'utilisateur, générer la clé et l'ajouter à `backend/.env` du dépôt principal (sans l'afficher dans la conversation) :

```bash
cd /d/2026/Projet/youtube-transcript-resume/backend
grep -q '^APP_SECRET_KEY=.' .env || echo "APP_SECRET_KEY=$(.venv-win/Scripts/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" >> .env
```

(Utiliser le venv du worktree si celui du dépôt principal n'a pas `cryptography`.) Rappeler à l'utilisateur de sauvegarder cette clé : sans elle, les clés saisies dans l'interface deviennent illisibles.

- [ ] **Step 3 : PR, fusion, Docker**

```bash
git -c credential.helper= -c credential.helper='!gh auth git-credential' push https://github.com/fbonhomme/youtube-transcript-resume.git feat/admin-api-keys
gh pr create --repo fbonhomme/youtube-transcript-resume --base main --head feat/admin-api-keys --title "feat: administration des clés API (accès local uniquement)"
gh pr merge <n°> --repo fbonhomme/youtube-transcript-resume --merge
# puis, dans le dépôt principal à jour :
docker compose cp backend:/app/data/yt_summaries.db backend/docker-backup-before-admin-<date>.db
docker compose build && docker compose up -d
curl -s localhost/health
curl -s -o /dev/null -w "%{http_code}\n" localhost/admin-api/keys/                          # 403
curl -s -o /dev/null -w "%{http_code}\n" -H "X-Admin-Access: local" localhost/admin-api/keys/  # 403
curl -s localhost:8080/admin-api/keys/                                                     # 200, clés masquées
```

Expected : logs backend `Running upgrade 0005 -> 0006` ; codes 403, 403 puis une réponse JSON avec `encryption_ready: true` et des clés masquées uniquement. Contrôle visuel de `http://localhost:8080/admin` (saisie, test, suppression) et de `http://localhost/admin` (message « Accès restreint »).

- [ ] **Step 4 : Nettoyage** — supprimer le worktree et la branche (locale et distante).
