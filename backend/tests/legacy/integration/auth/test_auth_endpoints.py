#!/usr/bin/env python3
"""
Integration tests for authentication endpoints.

Tests the authentication endpoints including:
- Login callback with token exchange
- Logout flow with cookie clearing and Keycloak redirect
- Token refresh functionality
- Landing page authentication state
"""

import sys
import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json
import requests
from fastapi.testclient import TestClient
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestLoginCallback:
    """Test OAuth login callback endpoint."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.env_patcher = patch.dict(os.environ, {
            'KEYCLOAK_DOMAIN': 'http://localhost:8080',
            'KEYCLOAK_REALM': 'test-realm',
            'KEYCLOAK_UI_CLIENT_ID': 'test-client',
            'KEYCLOAK_UI_CLIENT_SECRET': 'test-secret',
            'KEYCLOAK_REDIRECT_URI': 'http://localhost:8000/auth/callback'
        })
        self.env_patcher.start()
    
    def teardown_method(self):
        """Clean up after tests."""
        self.env_patcher.stop()
    
    @patch('requests.post')
    @patch('api.v0_1.endpoints.service.auth.get_cookie_security_settings')
    @patch('api.v0_1.endpoints.service.auth.logger')
    def test_keycloak_callback_success(self, mock_logger, mock_cookie_settings, mock_post):
        """Test successful OAuth callback with token exchange."""
        from api.v0_1.endpoints.service.auth import keycloak_callback
        
        # Mock cookie settings
        mock_cookie_settings.return_value = {
            "secure": False,
            "httponly": True,
            "samesite": "lax",
            "path": "/"
        }
        
        # Mock successful token response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        mock_post.return_value = mock_response
        
        # Mock request with authorization code
        mock_request = Mock()
        mock_request.query_params = {"code": "test_auth_code"}
        
        # Call the callback function
        result = await keycloak_callback(mock_request)
        
        # Verify redirect response
        assert isinstance(result, RedirectResponse)
        assert result.status_code == 302
        assert "/interface/home" in str(result.url)
        
        # Verify token exchange request was made
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "grant_type=authorization_code" in str(call_args)
        assert "code=test_auth_code" in str(call_args)
        
        # Verify logging
        mock_logger.info.assert_called()
        mock_logger.debug.assert_called()
    
    @patch('requests.post')
    @patch('api.v0_1.endpoints.service.auth.logger')
    def test_keycloak_callback_missing_code(self, mock_logger, mock_post):
        """Test callback endpoint with missing authorization code."""
        from api.v0_1.endpoints.service.auth import keycloak_callback
        from fastapi import HTTPException
        
        # Mock request without authorization code
        mock_request = Mock()
        mock_request.query_params = {}
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await keycloak_callback(mock_request)
        
        assert exc_info.value.status_code == 400
        assert "Missing authorization code" in str(exc_info.value.detail)
        
        # Verify no token exchange was attempted
        mock_post.assert_not_called()
        mock_logger.error.assert_called()
    
    @patch('requests.post')
    @patch('api.v0_1.endpoints.service.auth.logger')
    def test_keycloak_callback_token_exchange_failure(self, mock_logger, mock_post):
        """Test callback with failed token exchange."""
        from api.v0_1.endpoints.service.auth import keycloak_callback
        from fastapi import HTTPException
        
        # Mock failed token response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid authorization code"
        mock_post.return_value = mock_response
        
        # Mock request with authorization code
        mock_request = Mock()
        mock_request.query_params = {"code": "invalid_auth_code"}
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await keycloak_callback(mock_request)
        
        assert exc_info.value.status_code == 400
        assert "Failed to exchange code for tokens" in str(exc_info.value.detail)
        
        mock_logger.error.assert_called()


class TestLogoutEndpoint:
    """Test logout endpoint functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.env_patcher = patch.dict(os.environ, {
            'KEYCLOAK_DOMAIN': 'http://localhost:8080',
            'KEYCLOAK_REALM': 'test-realm',
            'KEYCLOAK_UI_CLIENT_ID': 'test-client',
            'KEYCLOAK_REDIRECT_URI': 'http://localhost:8000/auth/callback'
        })
        self.env_patcher.start()
    
    def teardown_method(self):
        """Clean up after tests."""
        self.env_patcher.stop()
    
    @patch('api.v0_1.endpoints.service.auth.get_cookie_security_settings')
    @patch('api.v0_1.endpoints.service.auth.logger')
    def test_logout_success(self, mock_logger, mock_cookie_settings):
        """Test successful logout flow."""
        from api.v0_1.endpoints.service.auth import logout
        from fastapi import Response
        
        # Mock cookie settings
        mock_cookie_settings.return_value = {
            "secure": False,
            "httponly": True,
            "samesite": "lax",
            "path": "/"
        }
        
        # Mock response object
        mock_response = Mock(spec=Response)
        
        # Call logout function
        result = await logout(mock_response)
        
        # Verify redirect response
        assert isinstance(result, RedirectResponse)
        assert result.status_code == 302
        
        # Verify redirect URL contains logout endpoint
        redirect_url = str(result.url)
        assert "protocol/openid-connect/logout" in redirect_url
        assert "post_logout_redirect_uri" in redirect_url
        assert "client_id=test-client" in redirect_url
        
        # Verify cookies were deleted
        assert mock_response.delete_cookie.call_count == 2  # access_token and refresh_token
        
        # Verify logging
        mock_logger.info.assert_called_with("Processing logout request")
        mock_logger.debug.assert_called()
    
    def test_logout_redirect_url_format(self):
        """Test that logout redirect URL is properly formatted."""
        from api.v0_1.endpoints.service.auth import logout
        from urllib.parse import urlparse, parse_qs
        
        with patch('api.v0_1.endpoints.service.auth.get_cookie_security_settings') as mock_settings:
            mock_settings.return_value = {"secure": False, "httponly": True, "samesite": "lax", "path": "/"}
            
            mock_response = Mock()
            result = await logout(mock_response)
            
            # Parse the redirect URL
            redirect_url = str(result.url)
            parsed_url = urlparse(redirect_url)
            query_params = parse_qs(parsed_url.query)
            
            # Verify URL structure
            assert parsed_url.path.endswith("/protocol/openid-connect/logout")
            assert "post_logout_redirect_uri" in query_params
            assert "client_id" in query_params
            
            # Verify parameter values
            assert query_params["client_id"][0] == "test-client"
            assert query_params["post_logout_redirect_uri"][0] == "http://localhost:8000/"


class TestRefreshTokenEndpoint:
    """Test refresh token endpoint functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.env_patcher = patch.dict(os.environ, {
            'KEYCLOAK_DOMAIN': 'http://localhost:8080',
            'KEYCLOAK_REALM': 'test-realm',
            'KEYCLOAK_UI_CLIENT_ID': 'test-client',
            'KEYCLOAK_UI_CLIENT_SECRET': 'test-secret'
        })
        self.env_patcher.start()
    
    def teardown_method(self):
        """Clean up after tests."""
        self.env_patcher.stop()
    
    @patch('requests.post')
    @patch('api.v0_1.endpoints.service.auth.get_cookie_security_settings')
    @patch('api.v0_1.endpoints.service.auth.logger')
    def test_refresh_token_success(self, mock_logger, mock_cookie_settings, mock_post):
        """Test successful token refresh."""
        from api.v0_1.endpoints.service.auth import refresh_token
        from fastapi import Response
        from fastapi.responses import JSONResponse
        
        # Mock cookie settings
        mock_cookie_settings.return_value = {
            "secure": False,
            "httponly": True,
            "samesite": "lax",
            "path": "/"
        }
        
        # Mock successful refresh response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        mock_post.return_value = mock_response
        
        # Mock request with refresh token
        mock_request = Mock()
        mock_request.cookies = {"refresh_token": "valid_refresh_token"}
        
        # Mock response object
        mock_fastapi_response = Mock(spec=Response)
        
        # Call refresh function
        result = await refresh_token(mock_request, mock_fastapi_response)
        
        # Verify JSON response
        assert isinstance(result, JSONResponse)
        assert result.status_code == 200
        
        # Verify token refresh request was made
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "grant_type=refresh_token" in str(call_args)
        assert "refresh_token=valid_refresh_token" in str(call_args)
        
        # Verify cookies were updated
        assert mock_fastapi_response.set_cookie.call_count == 2  # access_token and refresh_token
        
        # Verify logging
        mock_logger.info.assert_called()
    
    @patch('api.v0_1.endpoints.service.auth.logger')
    def test_refresh_token_missing(self, mock_logger):
        """Test refresh token endpoint with missing refresh token."""
        from api.v0_1.endpoints.service.auth import refresh_token
        from fastapi import HTTPException, Response
        
        # Mock request without refresh token
        mock_request = Mock()
        mock_request.cookies = {}
        
        mock_response = Mock(spec=Response)
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await refresh_token(mock_request, mock_response)
        
        assert exc_info.value.status_code == 401
        assert "No refresh token available" in str(exc_info.value.detail)
        
        mock_logger.warning.assert_called_with("Refresh token not found in cookies")
    
    @patch('requests.post')
    @patch('api.v0_1.endpoints.service.auth.get_cookie_security_settings')
    @patch('api.v0_1.endpoints.service.auth.logger')
    def test_refresh_token_invalid(self, mock_logger, mock_cookie_settings, mock_post):
        """Test refresh token endpoint with invalid refresh token."""
        from api.v0_1.endpoints.service.auth import refresh_token
        from fastapi import HTTPException, Response
        
        # Mock cookie settings
        mock_cookie_settings.return_value = {
            "secure": False,
            "httponly": True,
            "samesite": "lax",
            "path": "/"
        }
        
        # Mock failed refresh response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid refresh token"
        mock_post.return_value = mock_response
        
        # Mock request with invalid refresh token
        mock_request = Mock()
        mock_request.cookies = {"refresh_token": "invalid_refresh_token"}
        
        mock_fastapi_response = Mock(spec=Response)
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await refresh_token(mock_request, mock_fastapi_response)
        
        assert exc_info.value.status_code == 401
        assert "Token refresh failed" in str(exc_info.value.detail)
        
        # Verify invalid refresh token was cleared
        mock_fastapi_response.delete_cookie.assert_called_once_with(
            "refresh_token", **mock_cookie_settings.return_value
        )
        
        mock_logger.error.assert_called()


class TestLandingPageIntegration:
    """Test landing page authentication integration."""
    
    @patch('api.v0_1.endpoints.service.auth.validate_token_from_cookie')
    def test_landing_page_authenticated_context(self, mock_validate_token):
        """Test landing page template context for authenticated user."""
        from api.v0_1.app import App
        from fastapi.testclient import TestClient
        
        # Mock successful token validation
        mock_validate_token.return_value = {
            'preferred_username': 'testuser',
            'realm_access': {'roles': ['user']}
        }
        
        # Create test client
        app_instance = App()
        client = TestClient(app_instance.get_app())
        
        # Mock template response to capture context
        with patch('fastapi.templating.Jinja2Templates.TemplateResponse') as mock_template:
            mock_template.return_value = Mock()
            
            # Make request to landing page
            response = client.get("/")
            
            # Verify template was called with correct context
            mock_template.assert_called_once()
            call_args = mock_template.call_args[0]
            context = call_args[1]
            
            assert "is_authenticated" in context
            assert context["is_authenticated"] is True
    
    @patch('api.v0_1.endpoints.service.auth.validate_token_from_cookie')
    def test_landing_page_unauthenticated_context(self, mock_validate_token):
        """Test landing page template context for unauthenticated user."""
        from api.v0_1.app import App
        from fastapi.testclient import TestClient
        
        # Mock failed token validation
        mock_validate_token.return_value = None
        
        # Create test client
        app_instance = App()
        client = TestClient(app_instance.get_app())
        
        # Mock template response to capture context
        with patch('fastapi.templating.Jinja2Templates.TemplateResponse') as mock_template:
            mock_template.return_value = Mock()
            
            # Make request to landing page
            response = client.get("/")
            
            # Verify template was called with correct context
            mock_template.assert_called_once()
            call_args = mock_template.call_args[0]
            context = call_args[1]
            
            assert "is_authenticated" in context
            assert context["is_authenticated"] is False


if __name__ == "__main__":
    # Run tests directly if called as a script
    print("Running authentication endpoint integration tests...")
    
    # Run pytest
    import subprocess
    result = subprocess.run([
        sys.executable, '-m', 'pytest', __file__, '-v'
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    exit(result.returncode)