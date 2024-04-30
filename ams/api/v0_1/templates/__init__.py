import os
from fastapi.templating import Jinja2Templates

# Initialize Jinja2Templates
templates = Jinja2Templates(os.getenv("JINJA_TEMPLATES"))
