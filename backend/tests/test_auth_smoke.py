# backend/tests/test_auth_smoke.py
import os
import json
import time
from pathlib import Path

import pytest
import requests


# --- Config helpers ----------------------------------------------------------

def env(name: str, default: str | None = None) -> str:
    v = os.getenv(name, default)
    if v is None or v == "":
        raise RuntimeError(f"Missing required env var: {name}")
    return v

def kc_base() -> str:
    return env("KEYCLOAK_DOMAIN")  # e.g. http://keycloak:8080

def kc_realm() -> str:
    return env("KEYCLOAK_REALM")   # e.g. ams-portal

def kc_admin_client_id() -> str:
    return env("KEYCLOAK_ADMIN_CLIENT_ID")  # e.g. ams-portal-admin

def kc_issuer() -> str:
    # external issuer (must match token 'iss')
    return env("KEYCLOAK_TOKEN_ISSUER")     # e.g. http://localhost:8080/realms/ams-portal

def backend_base() -> str:
    # when running *inside* the backend container, localhost:8000 hits the app directly
    return os.getenv("BACKEND_BASE_URL", "http://localhost:8000")


# --- Token helpers -----------------------------------------------------------

def read_admin_client_secret() -> str:
    # Prefer the mounted Docker secret file
    p = Path(os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET_FILE", "/run/secrets/kc_admin_client_secret"))
    if not p.is_file():
        raise RuntimeError(f"Client secret file not found at {p}")
    secret = p.read_text().strip()
    if not secret:
        raise RuntimeError("Client secret file is empty")
    return secret

def get_client_credentials_token(timeout=10) -> str:
    token_url = f"{kc_base()}/realms/{kc_realm()}/protocol/openid-connect/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": kc_admin_client_id(),
        "client_secret": read_admin_client_secret(),
    }
    r = requests.post(token_url, data=data, timeout=timeout)
    try:
        payload = r.json()
    except json.JSONDecodeError:
        pytest.fail(f"Non-JSON response from token endpoint: HTTP {r.status_code}\n{r.text[:500]}")
    if r.status_code != 200:
        pytest.fail(f"Token request failed HTTP {r.status_code}: {json.dumps(payload)[:500]}")
    token = payload.get("access_token", "")
    if not token:
        pytest.fail(f"No access_token in response: {json.dumps(payload)[:500]}")
    return token


# --- Tests -------------------------------------------------------------------

def test_health_ready():
    url = f"{backend_base()}/api/health/ready"
    r = requests.get(url, timeout=5)
    assert r.status_code == 200, f"/api/health/ready returned {r.status_code}: {r.text[:200]}"

def test_validate_token_unauthorized():
    url = f"{backend_base()}/auth/validate"
    r = requests.get(url, timeout=5)  # no Authorization header
    assert r.status_code == 401, f"Expected 401 without token, got {r.status_code}: {r.text[:200]}"

def test_validate_token_authorized():
    # 1) obtain a client_credentials token for ams-portal-admin
    token = get_client_credentials_token()

    # 2) call backend /auth/validate
    url = f"{backend_base()}/auth/validate"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)

    # Helpful logging on failure
    assert r.status_code == 200, f"/auth/validate returned {r.status_code}: {r.text[:500]}"
    data = r.json()
    assert data.get("valid") is True, f"Unexpected payload: {data}"

    user = data.get("user") or {}
    # issuer must match external issuer configured in compose (and in KC tokens)
    iss = user.get("iss", "")
    assert iss == kc_issuer(), f"issuer mismatch: got {iss!r}, expected {kc_issuer()!r}"

    # sanity: azp should be our admin client id
    azp = user.get("azp", "")
    assert azp == kc_admin_client_id(), f"azp mismatch: got {azp!r}, expected {kc_admin_client_id()!r}"

    # optional: token still valid (exp > now)
    exp = user.get("exp", 0)
    assert exp and exp > int(time.time()), "Token appears expired"


def test_validate_token_with_garbage_token():
    url = f"{backend_base()}/auth/validate"
    r = requests.get(url, headers={"Authorization": "Bearer not.a.real.token"}, timeout=5)
    assert r.status_code == 401, f"Expected 401 with garbage token, got {r.status_code}: {r.text[:200]}"
