"""
Behave environment configuration for AMS Data Portal testing
"""
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def before_all(context):
    """Setup executed before all tests"""
    context.project_root = project_root
    context.config_file = project_root / "config.yaml"
    
    # Ensure we're in the correct directory for running setup scripts
    os.chdir(project_root)
    
    # Set up test environment variables
    os.environ.setdefault('PYTHONPATH', str(project_root))
    
def before_scenario(context, scenario):
    """Setup executed before each scenario"""
    pass
    
def after_scenario(context, scenario):
    """Cleanup executed after each scenario"""
    pass
    
def after_all(context):
    """Cleanup executed after all tests"""
    pass