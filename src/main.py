import dotenv
import os

dotenv.load_dotenv("./core/settings/.env")

import src.api.v0_1.endpoints as endpoints

from fastapi import Request, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Initialize security
app = FastAPI()

# Include routers
app.include_router(endpoints.asset_router)
app.include_router(endpoints.admin_router)
app.include_router(endpoints.auth_router)

# Mount static files
app.mount("/static", StaticFiles(directory=os.getenv('STATIC_FILES')), name="static")

# Initialize Jinja2Templates
templates = Jinja2Templates(os.getenv("JINJA_TEMPLATES"))

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
