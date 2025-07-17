import os
from typing import List

from fastapi import Request, FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from api.v0_1.endpoints import application_router
from api.v0_1.endpoints.service.models import model_registry


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
        @self.app.get("/",
                      response_class=HTMLResponse)
        def landing_page(request: Request):
            """
            Root for serving basic landing page with authentication state detection.

            Parameters:
            - **request** (Request): The request object.

            Returns:
            - **TemplateResponse**: The HTML response containing the landing page.
            """
            # Check if user is authenticated by validating the access token
            from api.v0_1.endpoints.service.auth import validate_token_from_cookie
            
            token_payload = validate_token_from_cookie(request)
            is_authenticated = token_payload is not None
            
            context = {
                "request": request,
                "is_authenticated": is_authenticated
            }
            return templates.TemplateResponse("/landing/index.html", context)

        @self.app.get("/test", response_class=JSONResponse)
        async def test_endpoint():
            return JSONResponse(content={"message": "The test endpoint_url is working."})

        @self.app.get("/logout")
        async def root_logout():
            """
            Root logout endpoint that redirects to the auth logout handler.
            This ensures the /logout URL in templates works correctly.
            """
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url="/auth/logout", status_code=302)

    def get_app(self):
        return self.app


app_instance = App()
app = app_instance.get_app()
