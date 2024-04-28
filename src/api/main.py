# Initialize Environment Variables
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic

from src.api.endpoints import admin, assets, auth

# Initialize security
security = HTTPBasic()
app = FastAPI()
# Include routers
app.include_router(assets.router)
app.include_router(admin.router)
app.include_router(auth.router)
# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
# Initialize templates
templates = Jinja2Templates(directory="templates")


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
    from uvicorn.config import LOGGING_CONFIG

    LOGGING_CONFIG["formatters"]["default"]["fmt"] = "%(asctime)s %(levelprefix)s %(message)s"
    uvicorn.run(app, host="127.0.0.1", port=8000)
