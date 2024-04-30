# Load environment variables
import dotenv
import os

dotenv.load_dotenv("./core/settings/.env")

path_envs = ['UUID_STORE', 'ENFORCER_MODEL', 'ENFORCER_POLICY', 'USER_POLICIES', 'JINJA_TEMPLATES',
             'ACCESS_AGENT_CONFIG', 'STATIC_FILES']

# Accessing path variables and converting to absolute paths
for path in path_envs:
    os.environ[path] = os.path.abspath(os.getenv(path))

dotenv.load_dotenv("./core/settings/.secrets")

import src.api.v0_1.endpoints as endpoints

from fastapi import Request, FastAPI
from fastapi.staticfiles import StaticFiles
from src.api.v0_1.templates import templates

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
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
