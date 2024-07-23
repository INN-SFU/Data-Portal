import os

from fastapi import Request, FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from api.v0_1.endpoints import application_router


class App:
    """
    Class representing the application.

    Initializes the FastAPI app, includes routers, mounts static files, adds CORS middleware,
    and loads templates.

    Usage:
        app = App()
        my_app = app.get_app()

    Attributes:
        app: The FastAPI application.
    """
    def __init__(self):
        self.app = FastAPI()

        # Include routers
        self.app.include_router(application_router)

        # Mount static files
        self.app.mount("/static", StaticFiles(directory=os.getenv('STATIC_FILES')), name="static")

        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Adjust as needed
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Load templates
        templates = Jinja2Templates(directory=os.getenv('JINJA_TEMPLATES'))

        # Landing
        @self.app.get("/", response_class=HTMLResponse)
        def read_root(request: Request):
            """
            Handler for the root endpoint.

            :param request: The incoming request object.
            :type request: Request
            :return: The rendered index.html template.
            :rtype: templates.TemplateResponse
            """
            return templates.TemplateResponse("/landing/index.html", {"request": request})

        @self.app.get("/test", response_class=HTMLResponse)
        async def test_endpoint():
            return "Test endpoint is working!"

    def get_app(self):
        return self.app


app_instance = App()
app = app_instance.get_app()
