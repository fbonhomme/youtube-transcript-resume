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
