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
