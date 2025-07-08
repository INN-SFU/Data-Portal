"""
Step definitions for configuration testing
"""
import os
import tempfile
import yaml
from behave import given, when, then
from envyaml import EnvYAML


@given('I have a valid configuration file')
def step_valid_config_file(context):
    """Create a temporary config file for testing"""
    config_content = {
        'keycloak': {
            'domain': '${KEYCLOAK_DOMAIN:-http://localhost:8080}',
            'realm': '${KEYCLOAK_REALM:-ams-portal}',
            'ui_client_id': '${KEYCLOAK_UI_CLIENT_ID:-ams-portal-ui}',
            'ui_client_secret': '${KEYCLOAK_UI_CLIENT_SECRET:-}',
            'admin_client_id': '${KEYCLOAK_ADMIN_CLIENT_ID:-ams-portal-admin}',
            'admin_client_secret': '${KEYCLOAK_ADMIN_CLIENT_SECRET:-secret}',
            'redirect_uri': '${KEYCLOAK_REDIRECT_URI:-http://localhost:8000/auth/callback}'
        },
        'system': {
            'reset': False
        },
        'uvicorn': {
            'host': '${AMS_HOST:-0.0.0.0}',
            'port': '${AMS_PORT:-8000}',
            'reload': '${AMS_RELOAD:-true}'
        },
        'logging': {
            'config': '${LOG_CONFIG:-./loggers/log_config.yaml}'
        }
    }
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_content, f)
        context.config_file = f.name


@given('I set environment variable "{var_name}" to "{value}"')
def step_set_env_var(context, var_name, value):
    """Set environment variable for testing"""
    os.environ[var_name] = value
    # Store original value for cleanup
    if not hasattr(context, 'original_env_vars'):
        context.original_env_vars = {}
    context.original_env_vars[var_name] = os.environ.get(var_name)


@when('I load the configuration with EnvYAML')
def step_load_config(context):
    """Load configuration using EnvYAML"""
    try:
        config_obj = EnvYAML(context.config_file, strict=False)
        context.app_config = config_obj.export()  # Export to dict
        context.config_loaded = True
        context.error = None
    except Exception as e:
        context.config_loaded = False
        context.error = str(e)


@then('the configuration should be loaded successfully')
def step_config_loaded_successfully(context):
    """Verify configuration was loaded without errors"""
    assert context.config_loaded, f"Configuration failed to load: {context.error}"
    assert context.app_config is not None


@then('the port should be an integer')
def step_port_is_integer(context):
    """Verify port is an integer type"""
    port = context.app_config['uvicorn']['port']
    assert isinstance(port, int), f"Port should be int but got {type(port)}: {port}"


@then('the reload setting should be a boolean')
def step_reload_is_boolean(context):
    """Verify reload setting is a boolean type"""
    reload_val = context.app_config['uvicorn']['reload']
    assert isinstance(reload_val, bool), f"Reload should be bool but got {type(reload_val)}: {reload_val}"


@then('the reset setting should be a boolean')
def step_reset_is_boolean(context):
    """Verify reset setting is a boolean type"""
    reset_val = context.app_config['system']['reset']
    assert isinstance(reset_val, bool), f"Reset should be bool but got {type(reset_val)}: {reset_val}"


@then('the port should be {expected_port:d}')
def step_port_equals(context, expected_port):
    """Verify port equals expected value"""
    port = context.app_config['uvicorn']['port']
    assert port == expected_port, f"Expected port {expected_port} but got {port}"


def after_scenario(context, scenario):
    """Cleanup after each scenario"""
    # Restore original environment variables
    if hasattr(context, 'original_env_vars'):
        for var_name, original_value in context.original_env_vars.items():
            if original_value is None:
                os.environ.pop(var_name, None)
            else:
                os.environ[var_name] = original_value
    
    # Clean up temporary config file
    if hasattr(context, 'config_file') and os.path.exists(context.config_file):
        os.unlink(context.config_file)