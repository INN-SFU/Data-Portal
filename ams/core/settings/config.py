from uvicorn.config import LOGGING_CONFIG
from casbin.util.log import DEFAULT_LOGGING


from core.data_access_manager import DataAccessManager
from core.connectivity.agents import ArbutusAgent

# Make uvicorn and casbin loggers use the same format
# uvicorn logger
LOGGING_CONFIG["formatters"]["default"]["fmt"] = "%(asctime)s [%(name)s]\t%(levelprefix)s\t%(message)s"
LOGGING_CONFIG["formatters"]["access"]["fmt"] = ('%(asctime)s [%(name)s]\t%(levelprefix)s\t%(client_addr)s - "%('
                                                 'request_line)s" %(status_code)s')
# casbin logger
DEFAULT_LOGGING["formatters"]["casbin_formatter"]["format"] = "{asctime} [{name}]\t{levelname}:\t\t{message}"

# Initialize DataAccessManager
dam = DataAccessManager()

# Initialize Data Access Point Agents
agents = [ArbutusAgent()]
