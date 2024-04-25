import logging
import json

from pathlib import Path
from logging.config import dictConfig
from dotenv import load_dotenv
from uvicorn.config import LOGGING_CONFIG
from casbin.util.log import DEFAULT_LOGGING

from src.api.internal.authorization import DataAccessManager
from src.api.internal.connectivity import ArbutusClient

# Initialize logger
# Make uvicorn and casbin loggers use the same format
# uvicorn logger
LOGGING_CONFIG["formatters"]["default"]["fmt"] = "%(asctime)s [%(name)s]\t%(levelprefix)s\t%(message)s"
LOGGING_CONFIG["formatters"]["access"]["fmt"] = ('%(asctime)s [%(name)s]\t%(levelprefix)s\t%(client_addr)s - "%('
                                                 'request_line)s" %(status_code)s')
# casbin logger
DEFAULT_LOGGING["formatters"]["casbin_formatter"]["format"] = "{asctime} [{name}]\t{levelname}:\t\t{message}"

logger = logging.getLogger(__name__)

# Load environment variables from .env file
logger.log(logging.INFO, "Loading environment variables...")
load_dotenv()

# Initialize DataAccessManager
logger.log(logging.INFO, "Initializing DataAccessManager...")
dam = DataAccessManager()
logger.log(logging.INFO, "DataAccessManager initialized.")

# Initialize Arbutus Client
logger.log(logging.INFO, "Initializing Arbutus Client...")
arbutus_client = ArbutusClient()
logger.log(logging.INFO, "Arbutus Client initialized.")
