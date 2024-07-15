import yaml

from core.data_access_manager import DataAccessManager
from core.connectivity.arbutus import ArbutusAgent

# Initialize DataAccessManager
dam = DataAccessManager()

# Initialize Data Access Point Agents
agents = [ArbutusAgent()]
