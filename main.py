import logging
import logging.config
import os
import yaml
import sys
import uvicorn

from dotenv import load_dotenv


# APP SPIN UP
if __name__ == "__main__":
    
    # Path to configuration file
    config_file = sys.argv[1]

    print("Loading configuration file...")
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    f.close()

    # ENVIRONMENT VARIABLES
    print("Loading environment variables...")
    # Get .env relative path
    prefix = os.path.abspath(os.path.dirname(__file__))
    env_path = prefix + '/core/settings/.env'
    load_dotenv(env_path)

    path_envs = ['UUID_STORE', 'ENFORCER_MODEL', 'ENFORCER_POLICY', 'USER_POLICIES', 'JINJA_TEMPLATES',
                 'ENDPOINT_CONFIGS', 'STATIC_FILES']

    # Accessing path variables and converting to absolute paths
    for path in path_envs:
        print(path)
        os.environ[path] = os.path.abspath(os.getenv(path))

    # ROOT DIRECTORY
    print('ROOT_DIRECTORY')
    ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
    os.environ['ROOT_DIRECTORY'] = ROOT_DIRECTORY


    # Keycloak Configuration (example)
    # Ensure you have these variables in your .env or config file:
    # KEYCLOAK_DOMAIN, REALM, CLIENT_ID, and optionally CLIENT_SECRET.
    print("Initializing Keycloak configuration...")
    os.environ['KEYCLOAK_DOMAIN'] = config['keycloak']['domain']
    os.environ['KEYCLOAK_REALM'] = config['keycloak']['realm']
    os.environ['KEYCLOAK_CLIENT_ID'] = config['keycloak']['client_id']
    os.environ['KEYCLOAK_CLIENT_SECRET'] = config['keycloak']['client_secret']
    os.environ['KEYCLOAK_REDIRECT_URI'] = config['keycloak']['redirect_uri']
    os.environ['KEYCLOAK_WELL_KNOWN_URL'] = f"{os.getenv('KEYCLOAK_DOMAIN')}/realms/{os.getenv('KEYCLOAK_REALM')}/.well-known/openid-configuration"
    os.environ['KEYCLOAK_ADMIN_USERNAME'] = config['keycloak']['admin_username']
    os.environ['KEYCLOAK_ADMIN_PASSWORD'] = config['keycloak']['admin_password']

    # RESET
    if config['system']['reset']:
        from core.settings.security.SYS_RESET import SYS_RESET

        SYS_RESET()

        # Set reset to False
        config['system']['reset'] = False
        # Write the updated configuration to the file
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        f.close()

    # LOG INITIALIZATION
    print("Initializing loggers...")
    with open(os.getenv('LOG_CONFIG'), 'r') as f:
        log_config = yaml.safe_load(f)
    logging.config.dictConfig(log_config)
    app_logger = logging.getLogger('app')

    # APP SECRETS
    app_logger.info("Loading secrets...")
    load_dotenv("core/settings/security/.secrets")

    app_logger.info("Starting application...")
    uvicorn.run(app='api.v0_1.app:app',
                host=config['uvicorn']['host'],
                port=config['uvicorn']['port'],
                reload=config['uvicorn']['reload'])
