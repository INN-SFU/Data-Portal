#!/usr/bin/env python3
"""
Keycloak production bootstrapper (REST-only)

Defaults point to your production Keycloak and common AMS names.
All values can be overridden via environment variables.

What it does:
- Admin auth (password grant)
- Ensure realm exists (optionally import from JSON if missing)
- Ensure service-account roles on the confidential admin client
- Ensure a 'roles' client scope and add it to that client’s defaults
- Ensure protocol mappers for the UI client (username + realm roles)
- Fetch (or rotate) the confidential client secret
- Persist secret to .env and/or backend/config.yaml
"""

from __future__ import annotations
import os
import sys
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from dotenv import load_dotenv  # optional
    load_dotenv()
except Exception:
    pass


# ----------------------------
# Configuration
# ----------------------------

@dataclass
class KCConfig:
    # Core
    base_url: str = os.getenv("KEYCLOAK_BASE_URL", "https://keycloak.rmcintos.cedar.researchcomputinggroup.ca")
    verify_tls: bool = os.getenv("KEYCLOAK_VERIFY_TLS", "true").lower() != "false"

    # Realms & clients
    admin_realm: str = os.getenv("KEYCLOAK_ADMIN_REALM", "master")
    realm: str = os.getenv("KEYCLOAK_REALM", "ams-portal")
    admin_cli_client_id: str = os.getenv("KEYCLOAK_ADMIN_CLI_CLIENT_ID", "admin-cli")

    # Confidential admin client (fetch secret for this)
    admin_client_id: str = os.getenv("KEYCLOAK_ADMIN_CLIENT_ID", "ams-portal-admin")

    # Public/UI client (add protocol mappers here). Default kept for FE/BE compatibility.
    ui_client_id: Optional[str] = os.getenv("KEYCLOAK_UI_CLIENT_ID", "ui-client-id")

    # Credentials
    admin_username: str = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
    admin_password: str = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")

    # Behavior
    regenerate_secret: bool = os.getenv("KEYCLOAK_REGENERATE_SECRET", "false").lower() == "true"
    write_secret_to_env: bool = os.getenv("WRITE_SECRET_TO_ENV", "true").lower() == "true"
    write_secret_to_yaml: bool = os.getenv("WRITE_SECRET_TO_YAML", "false").lower() == "true"

    # Paths
    realm_export_path: str = os.getenv("KEYCLOAK_REALM_EXPORT", "backend/config/keycloak-realm-export.json")
    project_root: Path = Path(os.getenv("PROJECT_ROOT", Path(__file__).resolve().parent))
    backend_root: Path = Path(os.getenv("BACKEND_ROOT", str(Path(__file__).resolve().parent / "backend")))
    config_yaml_path: Path = Path(os.getenv("CONFIG_YAML_PATH", str((Path(__file__).resolve().parent / "backend" / "config.yaml").resolve())))


def log(msg: str) -> None:
    print(msg, flush=True)


def mask(s: str, keep: int = 4) -> str:
    if not s:
        return ""
    return s[:keep] + "..." if len(s) > keep else "*" * len(s)


def requests_session(cfg: KCConfig) -> requests.Session:
    sess = requests.Session()
    retries = Retry(
        total=8,
        backoff_factor=0.6,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "POST", "PUT", "DELETE"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    sess.mount("http://", adapter)
    sess.mount("https://", adapter)
    sess.verify = cfg.verify_tls
    return sess


# ----------------------------
# REST helpers
# ----------------------------

def token_url(cfg: KCConfig) -> str:
    return f"{cfg.base_url}/realms/{cfg.admin_realm}/protocol/openid-connect/token"


def admin_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def admin_token(session: requests.Session, cfg: KCConfig) -> Optional[str]:
    log("Authenticating as Keycloak admin...")
    data = {
        "grant_type": "password",
        "client_id": cfg.admin_cli_client_id,
        "username": cfg.admin_username,
        "password": cfg.admin_password,
    }
    try:
        resp = session.post(token_url(cfg), data=data, timeout=15)
        if resp.status_code == 200:
            tok = resp.json().get("access_token")
            if tok:
                log("Admin token acquired")
                return tok
        log(f"Admin auth failed: {resp.status_code} {resp.text[:180]}")
    except Exception as e:
        log(f"Admin auth error: {e}")
    return None


def realm_exists(session: requests.Session, cfg: KCConfig, token: str) -> bool:
    url = f"{cfg.base_url}/admin/realms/{cfg.realm}"
    r = session.get(url, headers=admin_headers(token), timeout=15)
    return r.status_code == 200


def import_realm_if_needed(session: requests.Session, cfg: KCConfig, token: str) -> bool:
    if realm_exists(session, cfg, token):
        log(f"Realm '{cfg.realm}' exists")
        return True

    realm_file = (cfg.project_root / cfg.realm_export_path).resolve()
    if not realm_file.exists():
        log(f"Realm '{cfg.realm}' not found and no export file at: {realm_file}")
        return False

    try:
        data = json.loads(realm_file.read_text())
        url = f"{cfg.base_url}/admin/realms"
        r = session.post(url, headers=admin_headers(token), json=data, timeout=30)
        if r.status_code in (201, 409):
            log(f"Realm '{cfg.realm}' imported or already present")
            return True
        log(f"Realm import failed: {r.status_code} {r.text[:180]}")
        return False
    except Exception as e:
        log(f"Error importing realm: {e}")
        return False


def get_client_uuid(session: requests.Session, cfg: KCConfig, token: str, client_id: str) -> Optional[str]:
    url = f"{cfg.base_url}/admin/realms/{cfg.realm}/clients"
    r = session.get(url, headers=admin_headers(token), params={"clientId": client_id}, timeout=15)
    if r.status_code != 200:
        log(f"Unable to query client '{client_id}': {r.status_code}")
        return None
    arr = r.json()
    if not arr:
        log(f"Client '{client_id}' not found")
        return None
    return arr[0].get("id")


def ensure_service_account_roles(session: requests.Session, cfg: KCConfig, token: str, client_uuid: str) -> bool:
    # Resolve service-account user for the admin client
    sa_url = f"{cfg.base_url}/admin/realms/{cfg.realm}/clients/{client_uuid}/service-account-user"
    r = session.get(sa_url, headers=admin_headers(token), timeout=15)
    if r.status_code != 200:
        log(f"Could not resolve service-account user: {r.status_code}")
        return False
    service_user_id = r.json().get("id")
    log(f"Service account user id: {service_user_id}")

    # realm-management client UUID
    mgmt_uuid = get_client_uuid(session, cfg, token, "realm-management")
    if not mgmt_uuid:
        return False

    # roles from realm-management
    roles_url = f"{cfg.base_url}/admin/realms/{cfg.realm}/clients/{mgmt_uuid}/roles"
    r = session.get(roles_url, headers=admin_headers(token), timeout=15)
    if r.status_code != 200:
        log(f"Could not fetch realm-management roles: {r.status_code}")
        return False
    all_roles = r.json()

    needed = {"view-users", "manage-users", "query-users", "view-realm", "manage-realm"}
    to_assign = [role for role in all_roles if role.get("name") in needed]
    if not to_assign:
        log("No roles found to assign")
        return False

    assign_url = f"{cfg.base_url}/admin/realms/{cfg.realm}/users/{service_user_id}/role-mappings/clients/{mgmt_uuid}"
    r = session.post(assign_url, headers=admin_headers(token), json=to_assign, timeout=15)
    if r.status_code in (204, 200):
        log(f"Assigned {len(to_assign)} realm-management roles to service account")
        return True
    log(f"Failed to assign roles: {r.status_code} {r.text[:160]}")
    return False


def ensure_roles_client_scope(session: requests.Session, cfg: KCConfig, token: str) -> bool:
    list_url = f"{cfg.base_url}/admin/realms/{cfg.realm}/client-scopes"
    r = session.get(list_url, headers=admin_headers(token), timeout=15)
    if r.status_code != 200:
        log(f"Could not list client scopes: {r.status_code}")
        return False

    scopes = r.json()
    if any(s.get("name") == "roles" for s in scopes):
        log("'roles' client scope already present")
        return True

    payload = {
        "name": "roles",
        "description": "Add user realm/client roles into tokens",
        "protocol": "openid-connect",
        "attributes": {
            "include.in.token.scope": "true",
            "display.on.consent.screen": "true"
        },
        "protocolMappers": [
            {
                "name": "client roles",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usermodel-client-role-mapper",
                "consentRequired": False,
                "config": {
                    "userinfo.token.claim": "true",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "claim.name": "resource_access.${client_id}.roles",
                    "jsonType.label": "String",
                    "multivalued": "true"
                }
            },
            {
                "name": "realm roles",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usermodel-realm-role-mapper",
                "consentRequired": False,
                "config": {
                    "userinfo.token.claim": "true",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "claim.name": "realm_access.roles",
                    "jsonType.label": "String",
                    "multivalued": "true"
                }
            }
        ]
    }

    create_url = f"{cfg.base_url}/admin/realms/{cfg.realm}/client-scopes"
    r = session.post(create_url, headers=admin_headers(token), json=payload, timeout=20)
    if r.status_code in (201, 409):
        log("'roles' client scope ensured")
        return True
    log(f"Failed to create 'roles' scope: {r.status_code} {r.text[:160]}")
    return False


def add_scope_to_client_defaults(session: requests.Session, cfg: KCConfig, token: str, client_uuid: str, scope_name: str) -> bool:
    scopes_url = f"{cfg.base_url}/admin/realms/{cfg.realm}/client-scopes"
    r = session.get(scopes_url, headers=admin_headers(token), timeout=15)
    if r.status_code != 200:
        log(f"Could not get client scopes: {r.status_code}")
        return False
    scopes = r.json()
    scope = next((s for s in scopes if s.get("name") == scope_name), None)
    if not scope:
        log(f"Scope '{scope_name}' not found")
        return False

    add_url = f"{cfg.base_url}/admin/realms/{cfg.realm}/clients/{client_uuid}/default-client-scopes/{scope.get('id')}"
    r = session.put(add_url, headers=admin_headers(token), timeout=15)
    if r.status_code in (204, 200, 409):  # 409 if already present
        log(f"Ensured '{scope_name}' is a default scope for the client")
        return True
    log(f"Failed to add scope: {r.status_code} {r.text[:160]}")
    return False


def ensure_ui_protocol_mappers(session: requests.Session, cfg: KCConfig, token: str) -> bool:
    # Add protocol mappers to the UI client (username + realm roles).
    if not cfg.ui_client_id:
        log("No UI client id provided; skipping UI protocol mappers")
        return True

    client_uuid = get_client_uuid(session, cfg, token, cfg.ui_client_id)
    if not client_uuid:
        return False

    list_url = f"{cfg.base_url}/admin/realms/{cfg.realm}/clients/{client_uuid}/protocol-mappers/models"
    r = session.get(list_url, headers=admin_headers(token), timeout=15)
    if r.status_code != 200:
        log(f"Could not list protocol mappers: {r.status_code}")
        return False

    existing = {m.get("name") for m in r.json()}

    def create_mapper(payload: dict, name: str) -> None:
        if name in existing:
            log(f"Mapper '{name}' already present")
            return
        cr = session.post(list_url, headers=admin_headers(token), json=payload, timeout=15)
        if cr.status_code in (201, 409):
            log(f"Mapper '{name}' ensured")
        else:
            log(f"Mapper '{name}' failed: {cr.status_code} {cr.text[:140]}")

    create_mapper({
        "name": "username",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-usermodel-property-mapper",
        "config": {
            "user.attribute": "username",
            "jsonType.label": "String",
            "claim.name": "preferred_username",
            "id.token.claim": "true",
            "access.token.claim": "true",
            "userinfo.token.claim": "true"
        }
    }, "username")

    create_mapper({
        "name": "realm roles",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-usermodel-realm-role-mapper",
        "config": {
            "multivalued": "true",
            "userinfo.token.claim": "true",
            "id.token.claim": "true",
            "access.token.claim": "true",
            "claim.name": "realm_access.roles",
            "jsonType.label": "String"
        }
    }, "realm roles")

    return True


def fetch_client_secret(session: requests.Session, cfg: KCConfig, token: str, client_uuid: str) -> Optional[str]:
    url = f"{cfg.base_url}/admin/realms/{cfg.realm}/clients/{client_uuid}/client-secret"
    r = session.get(url, headers=admin_headers(token), timeout=15)
    if r.status_code == 200:
        return r.json().get("value")
    log(f"Failed to fetch client secret: {r.status_code} {r.text[:160]}")
    return None


def regenerate_client_secret(session: requests.Session, cfg: KCConfig, token: str, client_uuid: str) -> Optional[str]:
    url = f"{cfg.base_url}/admin/realms/{cfg.realm}/clients/{client_uuid}/client-secret"
    r = session.post(url, headers=admin_headers(token), timeout=15)
    if r.status_code in (200, 201):
        log("Client secret regenerated")
        return r.json().get("value")
    log(f"Failed to regenerate client secret: {r.status_code} {r.text[:160]}")
    return None


# ----------------------------
# Persisting the secret
# ----------------------------

def write_secret_to_env_file(cfg: KCConfig, secret: str) -> None:
    env_path = cfg.project_root / ".env"
    text = env_path.read_text() if env_path.exists() else ""
    if "KEYCLOAK_ADMIN_CLIENT_SECRET=" in text:
        new = re.sub(
            r"^KEYCLOAK_ADMIN_CLIENT_SECRET=.*?$",
            f"KEYCLOAK_ADMIN_CLIENT_SECRET={secret}",
            text,
            flags=re.MULTILINE,
        )
    else:
        new = text + ("" if text.endswith("\n") or not text else "\n") + f"KEYCLOAK_ADMIN_CLIENT_SECRET={secret}\n"
    env_path.write_text(new)
    log(f"Wrote client secret (masked: {mask(secret)}) to {env_path}")


def update_config_yaml_with_secret(cfg: KCConfig, secret: str) -> None:
    path = cfg.config_yaml_path
    if not path.exists():
        log(f"Config YAML not found at {path}; skipping YAML update")
        return
    content = path.read_text()
    updated = re.sub(
        r"(admin_client_secret:\s*\$KEYCLOAK_ADMIN_CLIENT_SECRET\|)[^|\n]+",
        r"\1" + secret,
        content,
    )
    if updated == content:
        updated = content.replace("your-admin-client-secret", secret)
    path.write_text(updated)
    log(f"Updated {path} with client secret (masked: {mask(secret)})")


# ----------------------------
# Orchestrator
# ----------------------------

def main() -> int:
    cfg = KCConfig()
    session = requests_session(cfg)

    tok = admin_token(session, cfg)
    if not tok:
        return 3

    if not import_realm_if_needed(session, cfg, tok):
        return 4

    admin_client_uuid = get_client_uuid(session, cfg, tok, cfg.admin_client_id)
    if not admin_client_uuid:
        return 5

    ensure_service_account_roles(session, cfg, tok, admin_client_uuid)

    if ensure_roles_client_scope(session, cfg, tok):
        add_scope_to_client_defaults(session, cfg, tok, admin_client_uuid, "roles")

    ensure_ui_protocol_mappers(session, cfg, tok)

    if cfg.regenerate_secret:
        log("Regenerating admin client secret as requested...")
        secret = regenerate_client_secret(session, cfg, tok, admin_client_uuid)
    else:
        secret = fetch_client_secret(session, cfg, tok, admin_client_uuid)

    if not secret:
        log("Could not obtain client secret")
        return 6

    if cfg.write_secret_to_env:
        write_secret_to_env_file(cfg, secret)
    if cfg.write_secret_to_yaml:
        update_config_yaml_with_secret(cfg, secret)

    log("Keycloak production configuration complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
