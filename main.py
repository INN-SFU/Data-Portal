import os
import yaml
import sys
import uvicorn
from dotenv import load_dotenv

from loggers.setup import setup_logging


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
                 'ACCESS_AGENT_CONFIG', 'STATIC_FILES']

    # Accessing path variables and converting to absolute paths
    for path in path_envs:
        os.environ[path] = os.path.abspath(os.getenv(path))

    # RESET
    if config['system']['reset']:
        from core.settings.SYS_RESET import SYS_RESET

        SYS_RESET()

    # LOG INITIALIZATION
    print("Initializing loggers...")
    loggers = setup_logging(config)
    app_logger = loggers['app']

    # APP SECRETS
    app_logger.info("Loading secrets...")
    load_dotenv("core/settings/.secrets")

    app_logger.info("Starting application...")
    uvicorn.run(app='api.v0_1.app:app',
                host=config['uvicorn']['host'],
                port=config['uvicorn']['port'],
                reload=config['uvicorn']['reload'])
