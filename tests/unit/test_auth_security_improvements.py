#!/usr/bin/env python3
"""
Unit tests for the authentication security improvements.

Tests the new authentication functions including:
- Token validation from cookies
- Cookie security settings
- Environment-based security configuration
- Landing page authentication detection
"""

import sys
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime, timedelta
import jwt as jwt_lib

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestTokenValidation:
    """Test token validation functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_request = Mock()
        self.mock_request.cookies = {}
        
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'KEYCLOAK_UI_CLIENT_ID': 'test-client',
            'KEYCLOAK_DOMAIN': 'http://localhost:8080',
            'KEYCLOAK_REALM': 'test-realm',
            'KEYCLOAK_REDIRECT_URI': 'http://localhost:8000/auth/callback'
        })
        self.env_patcher.start()
    
    def teardown_method(self):
        """Clean up after tests."""
        self.env_patcher.stop()
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.logger')
    def test_validate_token_from_cookie_success(self, mock_logger, mock_get_jwks_client):
        """Test successful token validation from cookie."""
        from api.v0_1.endpoints.service.auth import validate_token_from_cookie
        
        # Mock valid token
        valid_token = "valid.jwt.token"
        self.mock_request.cookies = {"access_token": valid_token}
        
        # Mock JWKS client
        mock_jwks_client = Mock()
        mock_signing_key = Mock()
        mock_signing_key.key = "mock_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_get_jwks_client.return_value = mock_jwks_client
        
        # Mock JWT decode
        expected_payload = {
            'preferred_username': 'testuser',
            'realm_access': {'roles': ['user']},
            'exp': int((datetime.now() + timedelta(hours=1)).timestamp()),
            'iat': int(datetime.now().timestamp()),
            'iss': 'http://localhost:8080/realms/test-realm',
            'sub': 'user-id'
        }
        
        with patch('jwt.decode', return_value=expected_payload):
            result = validate_token_from_cookie(self.mock_request)
            
            assert result == expected_payload
            mock_logger.debug.assert_called()
    
    @patch('api.v0_1.endpoints.service.auth.logger')
    def test_validate_token_from_cookie_no_token(self, mock_logger):
        """Test token validation when no token is present."""
        from api.v0_1.endpoints.service.auth import validate_token_from_cookie
        
        # No token in cookies
        self.mock_request.cookies = {}
        
        result = validate_token_from_cookie(self.mock_request)
        
        assert result is None
        mock_logger.debug.assert_called_with("No access token found in cookies")
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.logger')
    def test_validate_token_from_cookie_expired(self, mock_logger, mock_get_jwks_client):
        """Test token validation with expired token."""
        from api.v0_1.endpoints.service.auth import validate_token_from_cookie
        
        # Mock expired token
        expired_token = "expired.jwt.token"
        self.mock_request.cookies = {"access_token": expired_token}
        
        # Mock JWKS client
        mock_jwks_client = Mock()
        mock_signing_key = Mock()
        mock_signing_key.key = "mock_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_get_jwks_client.return_value = mock_jwks_client
        
        # Mock JWT decode to raise ExpiredSignatureError
        with patch('jwt.decode', side_effect=jwt_lib.ExpiredSignatureError("Token expired")):
            result = validate_token_from_cookie(self.mock_request)
            
            assert result is None
            mock_logger.debug.assert_called_with("Token has expired")
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.logger')
    def test_validate_token_from_cookie_invalid(self, mock_logger, mock_get_jwks_client):
        """Test token validation with invalid token."""
        from api.v0_1.endpoints.service.auth import validate_token_from_cookie
        
        # Mock invalid token
        invalid_token = "invalid.jwt.token"
        self.mock_request.cookies = {"access_token": invalid_token}
        
        # Mock JWKS client
        mock_jwks_client = Mock()
        mock_signing_key = Mock()
        mock_signing_key.key = "mock_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_get_jwks_client.return_value = mock_jwks_client
        
        # Mock JWT decode to raise InvalidTokenError
        with patch('jwt.decode', side_effect=jwt_lib.InvalidTokenError("Invalid token")):
            result = validate_token_from_cookie(self.mock_request)
            
            assert result is None
            mock_logger.debug.assert_called_with("Token validation failed: Invalid token")


class TestCookieSecuritySettings:
    """Test cookie security configuration functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear environment
        self.env_patcher = patch.dict(os.environ, {}, clear=True)
        self.env_patcher.start()
    
    def teardown_method(self):
        """Clean up after tests."""
        self.env_patcher.stop()
    
    @patch('api.v0_1.endpoints.service.auth.logger')
    def test_cookie_security_settings_development(self, mock_logger):
        """Test cookie security settings for development environment."""
        from api.v0_1.endpoints.service.auth import get_cookie_security_settings
        
        # Mock development environment (HTTP)
        with patch.dict(os.environ, {'KEYCLOAK_REDIRECT_URI': 'http://localhost:8000/auth/callback'}):
            settings = get_cookie_security_settings()
            
            expected_settings = {
                "secure": False,    # HTTP environment
                "httponly": True,   # Always prevent XSS
                "samesite": "lax",  # CSRF protection
                "path": "/"         # Available across app
            }
            
            assert settings == expected_settings
            mock_logger.debug.assert_called_with("Cookie security mode: development")
    
    @patch('api.v0_1.endpoints.service.auth.logger')
    def test_cookie_security_settings_production(self, mock_logger):
        """Test cookie security settings for production environment."""
        from api.v0_1.endpoints.service.auth import get_cookie_security_settings
        
        # Mock production environment (HTTPS)
        with patch.dict(os.environ, {'KEYCLOAK_REDIRECT_URI': 'https://example.com/auth/callback'}):
            settings = get_cookie_security_settings()
            
            expected_settings = {
                "secure": True,     # HTTPS environment
                "httponly": True,   # Always prevent XSS
                "samesite": "lax",  # CSRF protection
                "path": "/"         # Available across app
            }
            
            assert settings == expected_settings
            mock_logger.debug.assert_called_with("Cookie security mode: production")
    
    @patch('api.v0_1.endpoints.service.auth.logger')
    def test_cookie_security_settings_default(self, mock_logger):
        """Test cookie security settings with default configuration."""
        from api.v0_1.endpoints.service.auth import get_cookie_security_settings
        
        # No environment variable set, should use default
        settings = get_cookie_security_settings()
        
        expected_settings = {
            "secure": False,    # Default is HTTP (localhost)
            "httponly": True,   
            "samesite": "lax",  
            "path": "/"         
        }
        
        assert settings == expected_settings
        mock_logger.debug.assert_called_with("Cookie security mode: development")


class TestLandingPageAuthentication:
    """Test landing page authentication detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_request = Mock()
        self.mock_request.cookies = {}
    
    @patch('api.v0_1.endpoints.service.auth.validate_token_from_cookie')
    def test_landing_page_authenticated_user(self, mock_validate_token):
        """Test landing page shows correct state for authenticated user."""
        # Mock successful token validation
        mock_validate_token.return_value = {
            'preferred_username': 'testuser',
            'realm_access': {'roles': ['user']}
        }
        
        # Simulate the landing page logic
        from api.v0_1.endpoints.service.auth import validate_token_from_cookie
        
        token_payload = validate_token_from_cookie(self.mock_request)
        is_authenticated = token_payload is not None
        
        assert is_authenticated is True
        mock_validate_token.assert_called_once_with(self.mock_request)
    
    @patch('api.v0_1.endpoints.service.auth.validate_token_from_cookie')
    def test_landing_page_unauthenticated_user(self, mock_validate_token):
        """Test landing page shows correct state for unauthenticated user."""
        # Mock failed token validation
        mock_validate_token.return_value = None
        
        # Simulate the landing page logic
        from api.v0_1.endpoints.service.auth import validate_token_from_cookie
        
        token_payload = validate_token_from_cookie(self.mock_request)
        is_authenticated = token_payload is not None
        
        assert is_authenticated is False
        mock_validate_token.assert_called_once_with(self.mock_request)


class TestAdminRoleValidation:
    """Test admin role validation function."""
    
    def test_is_user_admin_realm_role(self):
        """Test admin detection from realm roles."""
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        admin_payload = {
            'preferred_username': 'admin',
            'realm_access': {'roles': ['admin', 'user']},
            'resource_access': {}
        }
        
        assert is_user_admin(admin_payload) is True
    
    def test_is_user_admin_client_role(self):
        """Test admin detection from client-specific roles."""
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        admin_payload = {
            'preferred_username': 'admin',
            'realm_access': {'roles': ['user']},
            'resource_access': {
                'test-client': {'roles': ['admin']}
            }
        }
        
        assert is_user_admin(admin_payload) is True
    
    def test_is_user_admin_regular_user(self):
        """Test regular user is not detected as admin."""
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        user_payload = {
            'preferred_username': 'user',
            'realm_access': {'roles': ['user']},
            'resource_access': {}
        }
        
        assert is_user_admin(user_payload) is False
    
    def test_is_user_admin_no_roles(self):
        """Test user with no roles is not detected as admin."""
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        no_roles_payload = {
            'preferred_username': 'user',
            'realm_access': {},
            'resource_access': {}
        }
        
        assert is_user_admin(no_roles_payload) is False
    
    def test_is_user_admin_missing_access(self):
        """Test user with missing access structures."""
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        minimal_payload = {
            'preferred_username': 'user'
        }
        
        assert is_user_admin(minimal_payload) is False


if __name__ == "__main__":
    # Run tests directly if called as a script
    print("Running authentication security improvement tests...")
    
    # Run pytest
    import subprocess
    result = subprocess.run([
        sys.executable, '-m', 'pytest', __file__, '-v'
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    exit(result.returncode)