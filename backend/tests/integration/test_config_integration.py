"""
Integration tests for configuration loading and environment setup.

These tests verify that the configuration system works correctly
with the actual main.py startup process.
"""

import pytest
import os
import tempfile
import yaml
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestConfigurationIntegration:
    """Integration tests for configuration and startup."""
    
    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing."""
        config_content = {
            'system': {
                'reset': False
            },
            'uvicorn': {
                'host': '$AMS_HOST|127.0.0.1',
                'port': '$AMS_PORT|8001',  # Use different port to avoid conflicts
                'reload': '$AMS_RELOAD|false'
            },
            'keycloak': {
                'domain': '$KEYCLOAK_DOMAIN|http://localhost:8080',
                'realm': '$KEYCLOAK_REALM|test-realm',
                'ui_client_id': '$KEYCLOAK_UI_CLIENT_ID|test-ui',
                'ui_client_secret': '$KEYCLOAK_UI_CLIENT_SECRET|',
                'admin_client_id': '$KEYCLOAK_ADMIN_CLIENT_ID|test-admin',
                'admin_client_secret': '$KEYCLOAK_ADMIN_CLIENT_SECRET|test-secret',
                'redirect_uri': '$KEYCLOAK_REDIRECT_URI|http://localhost:8001/auth/callback'
            },
            'logging': {
                'config': '$LOG_CONFIG|./loggers/log_config.yaml'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_content, f)
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    
    @pytest.fixture
    def temp_env_file(self):
        """Create temporary .env file."""
        env_content = '''
# Test environment file
ENFORCER_MODEL=./core/settings/managers/policies/casbin/model.conf
ENFORCER_POLICY=./core/settings/managers/policies/casbin/test_policies.csv
USER_POLICIES=./core/settings/managers/policies/casbin/user_policies
JINJA_TEMPLATES=./api/v0_1/templates
ENDPOINT_CONFIGS=./core/settings/managers/endpoints/configs
STATIC_FILES=./api/v0_1/static
'''
        
        # Create core/settings directory structure
        os.makedirs('core/settings', exist_ok=True)
        env_file = 'core/settings/.env'
        
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        yield env_file
        
        # Cleanup
        if os.path.exists(env_file):
            os.unlink(env_file)
    
    @pytest.fixture
    def temp_secrets_file(self):
        """Create temporary secrets file."""
        secrets_content = '''
# Test secrets file
JWT_SECRET_KEY=test-secret-key
ENCRYPTION_KEY=test-encryption-key
'''
        
        # Create security directory
        os.makedirs('core/settings/security', exist_ok=True)
        secrets_file = 'core/settings/security/.secrets'
        
        with open(secrets_file, 'w') as f:
            f.write(secrets_content)
        
        yield secrets_file
        
        # Cleanup
        if os.path.exists(secrets_file):
            os.unlink(secrets_file)
    
    def test_config_loading_with_defaults(self, temp_config_file, temp_env_file, temp_secrets_file):
        """Test that configuration loads correctly with default values."""
        from envyaml import EnvYAML
        
        # Test without environment variables set
        config = EnvYAML(temp_config_file, strict=False)
        
        # Verify default values are used and types are correct
        assert config['uvicorn']['host'] == '127.0.0.1'
        assert config['uvicorn']['port'] == 8001
        assert isinstance(config['uvicorn']['port'], int)
        assert config['uvicorn']['reload'] == False
        assert isinstance(config['uvicorn']['reload'], bool)
        
        # Verify Keycloak defaults
        assert config['keycloak']['domain'] == 'http://localhost:8080'
        assert config['keycloak']['realm'] == 'test-realm'
        assert config['keycloak']['ui_client_id'] == 'test-ui'
        
        # Verify system settings
        assert config['system']['reset'] == False
        assert isinstance(config['system']['reset'], bool)
    
    def test_config_loading_with_env_overrides(self, temp_config_file, temp_env_file, temp_secrets_file):
        """Test that environment variables properly override defaults."""
        from envyaml import EnvYAML
        
        # Set environment variables
        test_env = {
            'AMS_HOST': '0.0.0.0',
            'AMS_PORT': '9000',
            'AMS_RELOAD': 'true',
            'KEYCLOAK_DOMAIN': 'https://my-keycloak.com',
            'KEYCLOAK_REALM': 'my-realm'
        }
        
        with patch.dict(os.environ, test_env):
            config = EnvYAML(temp_config_file, strict=False)
            
            # Verify environment variables override defaults
            assert config['uvicorn']['host'] == '0.0.0.0'
            assert config['uvicorn']['port'] == 9000
            assert isinstance(config['uvicorn']['port'], int)
            assert config['uvicorn']['reload'] == True
            assert isinstance(config['uvicorn']['reload'], bool)
            
            # Verify Keycloak overrides
            assert config['keycloak']['domain'] == 'https://my-keycloak.com'
            assert config['keycloak']['realm'] == 'my-realm'
            assert config['keycloak']['ui_client_id'] == 'test-ui'  # Not overridden
    
    def test_config_export_for_environment_vars(self, temp_config_file, temp_env_file, temp_secrets_file):
        """Test that config.export() works correctly for environment variable setup."""
        from envyaml import EnvYAML
        
        config = EnvYAML(temp_config_file, strict=False)
        exported = config.export()
        
        # Verify export structure
        assert 'uvicorn' in exported
        assert 'keycloak' in exported
        assert 'system' in exported
        assert 'logging' in exported
        
        # Verify exported values have correct types
        assert isinstance(exported['uvicorn']['port'], int)
        assert isinstance(exported['uvicorn']['reload'], bool)
        assert isinstance(exported['system']['reset'], bool)
        
        # Verify nested structure is maintained
        assert exported['uvicorn']['host'] == '127.0.0.1'
        assert exported['keycloak']['domain'] == 'http://localhost:8080'
    
    def test_environment_variable_propagation(self, temp_config_file, temp_env_file, temp_secrets_file):
        """Test that configuration values are properly propagated to environment variables."""
        from envyaml import EnvYAML
        
        config = EnvYAML(temp_config_file, strict=False)
        
        # Simulate the environment variable setting from main.py
        original_env = os.environ.copy()
        
        try:
            # Set environment variables like main.py does
            for key, value in config.export().items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        env_key = f"{key}_{sub_key}".upper()
                        os.environ[env_key] = str(sub_value)
                else:
                    os.environ[key.upper()] = str(value)
            
            # Verify environment variables are set correctly
            assert os.environ['UVICORN_HOST'] == '127.0.0.1'
            assert os.environ['UVICORN_PORT'] == '8001'
            assert os.environ['UVICORN_RELOAD'] == 'False'
            assert os.environ['KEYCLOAK_DOMAIN'] == 'http://localhost:8080'
            assert os.environ['KEYCLOAK_REALM'] == 'test-realm'
            assert os.environ['SYSTEM_RESET'] == 'False'
            
        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)
    
    def test_config_validation_with_missing_files(self, temp_config_file):
        """Test configuration behavior when dependent files are missing."""
        from envyaml import EnvYAML
        
        # Test with missing .env file
        config = EnvYAML(temp_config_file, strict=False)
        
        # Should still load successfully
        assert config['uvicorn']['port'] == 8001
        assert config['keycloak']['domain'] == 'http://localhost:8080'
    
    def test_config_type_consistency(self, temp_config_file, temp_env_file, temp_secrets_file):
        """Test that configuration types remain consistent across different scenarios."""
        from envyaml import EnvYAML
        
        # Test with different environment variable types
        test_scenarios = [
            {},  # No env vars
            {'AMS_PORT': '8080'},  # String number
            {'AMS_PORT': '8080', 'AMS_RELOAD': 'true'},  # String boolean
            {'AMS_PORT': '8080', 'AMS_RELOAD': 'false'},  # String boolean false
        ]
        
        for env_vars in test_scenarios:
            with patch.dict(os.environ, env_vars, clear=False):
                config = EnvYAML(temp_config_file, strict=False)
                
                # Port should always be an integer
                assert isinstance(config['uvicorn']['port'], int)
                
                # Reload should always be a boolean
                assert isinstance(config['uvicorn']['reload'], bool)
                
                # Reset should always be a boolean
                assert isinstance(config['system']['reset'], bool)
    
    def test_config_with_empty_values(self, temp_config_file, temp_env_file, temp_secrets_file):
        """Test configuration handling of empty values."""
        from envyaml import EnvYAML
        
        # Test with empty environment variables
        test_env = {
            'KEYCLOAK_UI_CLIENT_SECRET': '',  # Empty string
        }
        
        with patch.dict(os.environ, test_env):
            config = EnvYAML(temp_config_file, strict=False)
            
            # Empty string gets converted to None by EnvYAML
            assert config['keycloak']['ui_client_secret'] is None
            
            # But other values should use defaults
            assert config['keycloak']['domain'] == 'http://localhost:8080'
    
    def test_config_error_handling(self):
        """Test configuration error handling with invalid files."""
        from envyaml import EnvYAML
        
        # Test with non-existent file
        with pytest.raises(FileNotFoundError):
            EnvYAML('/nonexistent/config.yaml', strict=False)
        
        # Test with invalid YAML
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            invalid_file = f.name
        
        try:
            with pytest.raises(yaml.YAMLError):
                EnvYAML(invalid_file, strict=False)
        finally:
            os.unlink(invalid_file)