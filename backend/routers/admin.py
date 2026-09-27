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
_ALLOWED_HOSTNAMES = {"localhost", "127.0.0.1", "::1"}


def _hostname_from_host_header(value: str) -> str | None:
    """Extrait le nom d'hôte d'un en-tête Host (sans le port). Gère la forme
    IPv6 entre crochets (`[::1]:8080`). Renvoie None si l'en-tête est absent
    ou ambigu (pas de crochets mais plusieurs `:`, ex. IPv6 nu)."""
    if not value:
        return None
    if value.startswith("["):
        end = value.find("]")
        if end == -1:
            return None
        return value[1:end].lower()
    if ":" in value:
        hostname, _, maybe_port = value.rpartition(":")
        if not maybe_port.isdigit():
            return None
        return hostname.lower()
    return value.lower()


def require_local_admin(request: Request) -> None:
    """N'autorise que la machine locale : client loopback (développement) ou,
    sous Docker, l'en-tête posé par le bloc nginx du port 127.0.0.1:8080.
    Exige en plus que l'en-tête Host désigne bien cette machine, pour se
    protéger d'un DNS rebinding (page malveillante qui résout un domaine
    public vers 127.0.0.1 et envoie Host: <domaine-attaquant>)."""
    hostname = _hostname_from_host_header(request.headers.get("host", ""))
    host_allowed = hostname in _ALLOWED_HOSTNAMES

    host = request.client.host if request.client else ""
    if host in _LOOPBACK and host_allowed:
        return
    if (
        settings.admin_trust_proxy_header
        and request.headers.get(ADMIN_ACCESS_HEADER) == "local"
        and host_allowed
    ):
        return
    raise HTTPException(
        status_code=403,
        detail="Administration accessible uniquement depuis cette machine",
    )


# Les routes d'administration modifient un état sensible (clés API) : elles
# doivent rester en PUT/DELETE avec un corps JSON. Le préflight CORS (déclenché
# par ces méthodes/en-têtes non "simples") constitue la protection CSRF — ne
# jamais ajouter de route GET ou POST sans corps qui change cet état.
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
