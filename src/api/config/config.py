import logging
import os

from dotenv import load_dotenv
from uvicorn.config import LOGGING_CONFIG
from casbin.util.log import DEFAULT_LOGGING
from fastapi.templating import Jinja2Templates

from src.api.internal.authorization import DataAccessManager



# Initialize logger
# Make uvicorn and casbin loggers use the same format
# uvicorn logger
LOGGING_CONFIG["formatters"]["default"]["fmt"] = "%(asctime)s [%(name)s]\t%(levelprefix)s\t%(message)s"
LOGGING_CONFIG["formatters"]["access"]["fmt"] = ('%(asctime)s [%(name)s]\t%(levelprefix)s\t%(client_addr)s - "%('
                                                 'request_line)s" %(status_code)s')
# casbin logger
DEFAULT_LOGGING["formatters"]["casbin_formatter"]["format"] = "{asctime} [{name}]\t{levelname}:\t\t{message}"

logger = logging.getLogger(__name__)

# Initialize Jinja2Templates
logger.log(logging.INFO, "Initializing Jinja2Templates...")
templates = Jinja2Templates(os.getenv("JINJA_TEMPLATES"))

# Initialize DataAccessManager
logger.log(logging.INFO, "Initializing DataAccessManager...")
dam = DataAccessManager()


