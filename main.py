import os
import logging
from dotenv import load_dotenv

# Get .env relative path
prefix = os.path.abspath(os.path.dirname(__file__))
env_path = prefix + '/core/settings/.env'
load_dotenv(env_path)

path_envs = ['UUID_STORE', 'ENFORCER_MODEL', 'ENFORCER_POLICY', 'USER_POLICIES', 'JINJA_TEMPLATES',
             'ACCESS_AGENT_CONFIG', 'STATIC_FILES']

# Accessing path variables and converting to absolute paths
for path in path_envs:
    os.environ[path] = os.path.abspath(os.getenv(path))

load_dotenv("core/settings/.secrets")

import api.v0_1.endpoints as endpoints

from fastapi import Request, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from api.v0_1.templates import templates

# Initialize security
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
    allow_origins=["http://127.0.0.1:8000"],  # Adjust as needed
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


if __name__ == "__main__":
    import yaml
    import uvicorn

    from casbin.util.log import DEFAULT_LOGGING
    from casbin.util.log import configure_logging
    from uvicorn.config import LOGGING_CONFIG

    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    f.close()

    # Configure logging
    LOG_LEVEL = logging.DEBUG if config.get("debug", False) else logging.INFO

    # Make uvicorn and casbin loggers use the same format
    # uvicorn logger
    GREEN = "\033[32m"
    RESET = "\033[0m"
    LOGGING_CONFIG["formatters"]["default"]["fmt"] = "%(asctime)s [%(name)s]\t%(levelprefix)s\t%(message)s"
    LOGGING_CONFIG["formatters"]["access"]["fmt"] = ('%(asctime)s [%(name)s]\t%(levelprefix)s\t%(client_addr)s - "%('
                                                     'request_line)s" %(status_code)s')
    LOGGING_CONFIG["loggers"]["uvicorn"]["level"] = LOG_LEVEL

    # Update casbin logging configuration
    # fixme: This is not working, format not showing up on casbin log messages
    DEFAULT_LOGGING["formatters"]["casbin_formatter"]["format"] = (
        f"{RESET}{{asctime}} [{{name}}{RESET}]\t{GREEN}{{levelname}}{RESET}:\t\t{{message}}"
    )
    DEFAULT_LOGGING['handlers']['console']['level'] = LOG_LEVEL

    configure_logging(DEFAULT_LOGGING)

    # Reset the system if required
    if config['uvicorn']['reset']:
        from core.settings.SYS_RESET import SYS_RESET

        SYS_RESET()

    uvicorn.run('main:app', host=config['uvicorn']['host'], port=config['uvicorn']['port'],
                reload=config['uvicorn']['reload'])
