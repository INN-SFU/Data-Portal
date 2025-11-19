import os
import logging.config
from pathlib import Path

import uvicorn
import yaml


if __name__ == "__main__":

    # ---- Required app vars (must be set via .env.development or environment)
    required_vars = ["AMS_HOST", "AMS_PORT", "AMS_RELOAD", "API_VERSION", "LOG_DIR", "LOG_LEVEL"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}. Load from backend/.env.development")

    # ---- Logging
    print("Initializing loggers...")
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

    # ---- Read Keycloak admin client secret from file
    logging.info("Loading Keycloak admin client secret...")
    secret_file = os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET_FILE")
    if not secret_file:
        raise RuntimeError("Missing required env: KEYCLOAK_ADMIN_CLIENT_SECRET_FILE")
    if not Path(secret_file).exists():
        raise RuntimeError(f"Keycloak admin client secret file not found: {secret_file}")

    with open(secret_file, 'r') as f:
        secret = f.read().strip()
    if not secret:
        raise RuntimeError(f"Keycloak admin client secret file is empty: {secret_file}")

    os.environ["KEYCLOAK_ADMIN_CLIENT_SECRET"] = secret
    logging.info(f"Loaded Keycloak admin client secret from {secret_file}")

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

    # ---- Run server
    host = os.getenv("AMS_HOST", "0.0.0.0")
    port = int(os.getenv("AMS_PORT", "8000"))
    reload = os.getenv("AMS_RELOAD", "false").lower() == "true"
    os.environ["APP_HOST"] = host
    os.environ["APP_PORT"] = str(port)

    # Configure uvicorn to use our log config
    log_config = logging.getLogger().manager.loggerDict
    uvicorn.run(
        app="api.v0_1.app:app",
        host=host,
        port=port,
        reload=reload,
        log_config=None,  # Disable uvicorn's default log config, use our logging config
        access_log=True
    )
