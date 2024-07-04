import os

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
from api.v0_1.templates import templates

# Initialize security
app = FastAPI()

# Include routers
app.include_router(endpoints.asset_router)
app.include_router(endpoints.admin_router)
app.include_router(endpoints.auth_router)

# Mount static files
app.mount("/static", StaticFiles(directory=os.getenv('STATIC_FILES')), name="static")


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

    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    if config['uvicorn']['reset']:
        from core.settings.SYS_RESET import SYS_RESET

        SYS_RESET()

    uvicorn.run(app, host=config['uvicorn']['host'], port=config['uvicorn']['port'], reload=config['uvicorn']['reload'])
