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
    merged = {"Host": "localhost", **(headers or {})}
    raw = [(k.lower().encode(), v.encode()) for k, v in merged.items()]
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


# ── Protection anti DNS rebinding (en-tête Host) ────────────────────────────

def test_require_local_admin_rejects_loopback_with_foreign_host(no_trust_proxy):
    with pytest.raises(HTTPException) as exc:
        require_local_admin(_request("127.0.0.1", {"Host": "evil.example"}))
    assert exc.value.status_code == 403


def test_require_local_admin_accepts_loopback_with_port_in_host(no_trust_proxy):
    require_local_admin(_request("127.0.0.1", {"Host": "localhost:8000"}))


def test_require_local_admin_rejects_trusted_proxy_with_foreign_host(trust_proxy):
    with pytest.raises(HTTPException) as exc:
        require_local_admin(
            _request("172.18.0.3", {"X-Admin-Access": "local", "Host": "attacker.tld:8080"})
        )
    assert exc.value.status_code == 403


def test_require_local_admin_accepts_trusted_proxy_with_localhost_host(trust_proxy):
    require_local_admin(
        _request("172.18.0.3", {"X-Admin-Access": "local", "Host": "localhost:8080"})
    )


def test_require_local_admin_accepts_ipv6_loopback_with_bracketed_host(no_trust_proxy):
    require_local_admin(_request("::1", {"Host": "[::1]:8080"}))


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


def test_put_key_with_control_character_returns_422(admin, secret):
    value = "sk-or-abc\ndef123456"
    r = admin.put("/admin-api/keys/openrouter", json={"value": value})
    assert r.status_code == 422
    assert value not in r.text


def test_put_key_with_non_ascii_returns_422(admin, secret):
    value = "sk-or-…abc1234"
    r = admin.put("/admin-api/keys/openrouter", json={"value": value})
    assert r.status_code == 422


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


# ── Corps de requête malformé (422) ──────────────────────────────────────────

def test_malformed_body_does_not_echo_key(admin, secret):
    r = admin.put("/admin-api/keys/openrouter", json={"key": _KEY})
    assert r.status_code == 422
    assert _KEY not in r.text


def test_bare_string_body_does_not_echo_key(admin, secret):
    r = admin.put("/admin-api/keys/openrouter", json=_KEY)
    assert r.status_code == 422
    assert _KEY not in r.text


def test_validation_errors_elsewhere_unchanged(client):
    r = client.post("/summaries/", json={"url": "not-a-youtube-url"})
    assert r.status_code == 422
    assert any("input" in item for item in r.json()["detail"])
