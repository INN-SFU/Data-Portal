import logging
import logging.config
import os
import sys
import uvicorn
import yaml

from dotenv import load_dotenv


# APP SPIN UP
if __name__ == "__main__":

    print("Using environment variables directly (no config file)...")

    # DEBUG: Check secret availability immediately when Python starts
    secret = os.getenv('KEYCLOAK_ADMIN_CLIENT_SECRET')
    print(f"DEBUG: Python startup - Secret available: {'YES' if secret else 'NO'}")
    if secret:
        print(f"DEBUG: Python startup - Secret length: {len(secret)}")
        print(f"DEBUG: Python startup - Secret preview: {secret[:8]}...")

    print("DEBUG: All KEYCLOAK environment variables at Python startup:")
    for key, value in os.environ.items():
        if 'KEYCLOAK' in key:
            display_value = value[:8] + '...' if 'SECRET' in key and value else value
            print(f"DEBUG:   {key}={display_value}")

    # Set defaults for required environment variables if not set
    os.environ.setdefault('SYSTEM_RESET', 'false')
    os.environ.setdefault('AMS_HOST', '0.0.0.0')
    os.environ.setdefault('AMS_PORT', '8000')
    os.environ.setdefault('AMS_RELOAD', 'false')
    os.environ.setdefault('API_VERSION', '0_1')

    # ENVIRONMENT VARIABLES
    print("Loading environment variables...")
    # Get .env relative path
    prefix = os.path.abspath(os.path.dirname(__file__))
    env_path = prefix + '/core/settings/.env'
    load_dotenv(env_path)

    path_envs = ['ENFORCER_MODEL', 'ENFORCER_POLICY', 'USER_POLICIES', 'INSTANCE_CONFIGS']

    # Accessing path variables and converting to absolute paths
    for path in path_envs:
        print(f"\t{path}={os.getenv(path)}")
        os.environ[path] = os.path.abspath(os.getenv(path))

    # ROOT DIRECTORY
    print('ROOT_DIRECTORY')
    ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
    os.environ['ROOT_DIRECTORY'] = ROOT_DIRECTORY

    # Keycloak Configuration - derived URLs from environment variables
    print("Setting up Keycloak derived URLs...")
    os.environ[
        'KEYCLOAK_WELL_KNOWN_URL'] = f"{os.getenv('KEYCLOAK_DOMAIN')}/realms/{os.getenv('KEYCLOAK_REALM')}/.well-known/openid-configuration"
    os.environ[
        'KEYCLOAK_LOGIN_URL'] = f"{os.getenv('KEYCLOAK_DOMAIN')}/realms/{os.getenv('KEYCLOAK_REALM')}/protocol/openid-connect/auth" \
                                f"?client_id={os.getenv('KEYCLOAK_UI_CLIENT_ID')}" \
                                f"&redirect_uri={os.getenv('KEYCLOAK_REDIRECT_URI')}" \
                                f"&response_type=code"

    # RESET
    if os.getenv('SYSTEM_RESET', 'false').lower() == 'true':
        from core.settings.security.SYS_RESET import SYS_RESET
        print("Performing system reset...")
        SYS_RESET()
        # Note: In container environment, reset flag is not persisted

    # LOG INITIALIZATION
    print("Initializing loggers...")

    # Set up logging environment variables before loading config
    os.environ.setdefault('LOG_DIR', os.path.join(os.getcwd(), 'data', 'logs'))
    os.environ.setdefault('LOG_LEVEL', 'INFO')

    log_config_path = os.getenv('LOG_CONFIG', './loggers/log_config.yaml')
    log_config_path = os.path.abspath(log_config_path)
    with open(log_config_path, 'r') as f:
        log_config_content = f.read()

    # Substitute environment variables in the log config
    import os
    log_config_content = log_config_content.replace('${LOG_DIR}', os.environ['LOG_DIR'])
    log_config_content = log_config_content.replace('${LOG_LEVEL}', os.environ['LOG_LEVEL'])

    log_config = yaml.safe_load(log_config_content)
    logging.config.dictConfig(log_config)
    app_logger = logging.getLogger('app')

    # APP SECRETS
    app_logger.info("Loading secrets...")
    load_dotenv("core/settings/security/.secrets")

    app_logger.info("Starting application...")

    # Get server configuration from environment
    host = os.getenv('AMS_HOST', '0.0.0.0')
    port = int(os.getenv('AMS_PORT', '8000'))
    reload = os.getenv('AMS_RELOAD', 'false').lower() == 'true'

    os.environ['APP_HOST'] = host
    os.environ['APP_PORT'] = str(port)

    uvicorn.run(app='api.v0_1.app:app',
                host=host,
                port=port,
                reload=reload)
