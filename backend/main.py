import os
import logging.config
from pathlib import Path

import uvicorn
import yaml


if __name__ == "__main__":

    # ---- Required app vars (Compose is source of truth; set safe defaults for local runs)
    os.environ.setdefault("SYSTEM_RESET", "false")
    os.environ.setdefault("AMS_HOST", "0.0.0.0")
    os.environ.setdefault("AMS_PORT", "8000")
    os.environ.setdefault("AMS_RELOAD", "false")
    os.environ.setdefault("API_VERSION", "0_1")

    # ---- Logging
    print("Initializing loggers...")
    os.environ.setdefault("LOG_DIR", str((Path.cwd() / "data" / "logs").resolve()))
    os.environ.setdefault("LOG_LEVEL", "INFO")
    log_config_path = Path(os.getenv("LOG_CONFIG", "./loggers/log_config.yaml")).resolve()
    with open(log_config_path, "r") as f:
        cfg_text = f.read().replace("${LOG_DIR}", os.environ["LOG_DIR"]).replace("${LOG_LEVEL}", os.environ["LOG_LEVEL"])
    logging.config.dictConfig(yaml.safe_load(cfg_text))
    logging.getLogger("app").info("Starting application...")

    # ---- Resolve/absolutize paths (provided by Compose)
    path_envs = ["ENFORCER_MODEL", "ENFORCER_POLICY", "USER_POLICIES", "INSTANCE_CONFIGS"]
    for k in path_envs:
        v = os.getenv(k)
        if not v:
            raise RuntimeError(f"Missing required env: {k}")
        os.environ[k] = str(Path(v).resolve())
        logging.info(f"{k}={os.environ[k]}")

    # ---- Root dir (informational)
    prefix = Path(__file__).parent.resolve()
    os.environ["ROOT_DIRECTORY"] = str(prefix)

    # ---- Keycloak derived URLs (internal service address). Do NOT touch TOKEN_ISSUER here.
    logging.info("Setting up Keycloak derived URLs...")
    kc_domain = os.getenv("KEYCLOAK_DOMAIN")
    kc_realm = os.getenv("KEYCLOAK_REALM")
    os.environ["KEYCLOAK_WELL_KNOWN_URL"] = f"{kc_domain}/realms/{kc_realm}/.well-known/openid-configuration"
    os.environ["KEYCLOAK_LOGIN_URL"] = (
        f"{kc_domain}/realms/{kc_realm}/protocol/openid-connect/auth"
        f"?client_id={os.getenv('KEYCLOAK_UI_CLIENT_ID')}"
        f"&redirect_uri={os.getenv('KEYCLOAK_REDIRECT_URI')}"
        f"&response_type=code"
    )

    # ---- Optional system reset
    if os.getenv("SYSTEM_RESET", "false").lower() == "true":
        from core.settings.security.SYS_RESET import SYS_RESET
        logging.info("Performing system reset...")
        SYS_RESET()

    # ---- Run server
    host = os.getenv("AMS_HOST", "0.0.0.0")
    port = int(os.getenv("AMS_PORT", "8000"))
    reload = os.getenv("AMS_RELOAD", "false").lower() == "true"
    os.environ["APP_HOST"] = host
    os.environ["APP_PORT"] = str(port)

    uvicorn.run(app="api.v0_1.app:app", host=host, port=port, reload=reload)
