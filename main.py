import os
import logging.config
import logging
import yaml
from dotenv import load_dotenv

# LOG INITIALIZATION
def setup_logging(config_path='config.yaml'):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    f.close()

    logging.config.fileConfig('logging.conf', disable_existing_loggers=False)

    # Set logging levels based on the YAML configuration
    log_levels = config['logging']['level']
    for logger_name, level in log_levels.items():
        logging.getLogger(logger_name).setLevel(level)

    return config

config = setup_logging()

# Create loggers
app_logger = logging.getLogger('app')
casbin_logger = logging.getLogger('casbin')

app_logger.info("Starting application")

# ENVIRONMENT VARIABLES
# Get .env relative path
prefix = os.path.abspath(os.path.dirname(__file__))
env_path = prefix + '/core/settings/.env'
load_dotenv(env_path)

path_envs = ['UUID_STORE', 'ENFORCER_MODEL', 'ENFORCER_POLICY', 'USER_POLICIES', 'JINJA_TEMPLATES',
             'ACCESS_AGENT_CONFIG', 'STATIC_FILES']

# Accessing path variables and converting to absolute paths
for path in path_envs:
    os.environ[path] = os.path.abspath(os.getenv(path))

# APP SECRETS
load_dotenv("core/settings/.secrets")

# IMPORTS
import api.v0_1.endpoints as endpoints

from fastapi import Request, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from api.v0_1.templates import templates

# APP INITIALIZATION
app = FastAPI()

# Include routers
app.include_router(endpoints.asset_router)
app.include_router(endpoints.admin_router)
app.include_router(endpoints.auth_router)

# Mount static files
app.mount("/static", StaticFiles(directory=os.getenv('STATIC_FILES')), name="static")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/")
def read_root(request: Request):
    """
    Handler for the root endpoint.

    :param request: The incoming request object.
    :type request: Request
    :return: The rendered index.html template.
    :rtype: templates.TemplateResponse
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/test", response_class=HTMLResponse)
async def test_endpoint():
    return "Test endpoint is working!"


if __name__ == "__main__":
    import uvicorn

    # Reset the system if required
    if config['uvicorn']['reset']:
        from core.settings.SYS_RESET import SYS_RESET
        SYS_RESET()

    uvicorn.run('main:app', host=config['uvicorn']['host'], port=config['uvicorn']['port'],
                reload=config['uvicorn']['reload'])
