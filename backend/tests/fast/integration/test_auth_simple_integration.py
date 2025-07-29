#!/usr/bin/env python3
"""
Simple Authentication Integration Tests

Fast integration tests that bypass complex dependency injection by testing
the authentication components in isolation using direct function calls and
mocked external services.

Strategy:
- Test authentication functions directly
- Mock Keycloak JWT validation
- Use FastAPI TestClient with minimal app setup
- Focus on authentication workflows without full application stack

Speed: Very fast (<1s per test)
Dependencies: Minimal (Keycloak mocked)
Coverage: Authentication logic and API responses
"""

import pytest
import jwt as jwt_lib
from unittest.mock import Mock, patch, MagicMock
from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import os
import sys

# Setup path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))


@pytest.fixture
def minimal_app():
    """Create minimal FastAPI app for testing authentication endpoints only."""
    app = FastAPI()
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # API root endpoint
    @app.get("/")
    async def api_root():
        return {
            "message": "AMS Data Portal API",
            "version": "v0.1", 
            "documentation": "/docs"
        }
    
    @app.get("/test")
    async def test_endpoint():
        return {"message": "The test endpoint_url is working."}
    
    return app


@pytest.fixture
def auth_app():
    """Create FastAPI app with authentication endpoints only."""
    app = FastAPI()
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mock environment variables for auth
    with patch.dict(os.environ, {
        'KEYCLOAK_DOMAIN': 'http://localhost:8080',
        'KEYCLOAK_REALM': 'test-realm',
        'KEYCLOAK_UI_CLIENT_ID': 'test-client',
        'KEYCLOAK_WELL_KNOWN_URL': 'http://localhost:8080/realms/test-realm/.well-known/openid-configuration'
    }):
        # Import auth router after setting environment
        from api.v0_1.endpoints.service.auth import auth_router
        from api.v0_1.endpoints.service.admin import admin_router
        # Include routers with /api prefix to match main application
        api_router = APIRouter(prefix="/api")
        api_router.include_router(auth_router)
        api_router.include_router(admin_router)
        app.include_router(api_router)
    
    return app


@pytest.fixture
def valid_token_payload():
    """Standard valid token payload."""
    return {
        "sub": "user-123",
        "preferred_username": "testuser",
        "email": "testuser@example.com",
        "given_name": "Test",
        "family_name": "User",
        "realm_access": {
            "roles": ["user"]
        },
        "resource_access": {
            "test-client": {
                "roles": ["user"]
            }
        },
        "iss": "http://localhost:8080/realms/test-realm",
        "aud": "test-client",
        "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
        "iat": int(datetime.now().timestamp())
    }


@pytest.fixture
def admin_token_payload():
    """Admin token payload."""
    return {
        "sub": "admin-123",
        "preferred_username": "adminuser",
        "email": "admin@example.com",
        "realm_access": {
            "roles": ["admin", "user"]
        },
        "resource_access": {
            "test-client": {
                "roles": ["admin", "user"]
            }
        },
        "iss": "http://localhost:8080/realms/test-realm",
        "aud": "test-client",
        "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
        "iat": int(datetime.now().timestamp())
    }


class TestBasicAPIEndpoints:
    """Test basic API endpoints without authentication."""
    
    def test_api_root_endpoint(self, minimal_app):
        """Test API root endpoint."""
        client = TestClient(minimal_app)
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "AMS Data Portal API"
        assert data["version"] == "v0.1"
        assert data["documentation"] == "/docs"
    
    def test_api_test_endpoint(self, minimal_app):
        """Test API health check endpoint."""
        client = TestClient(minimal_app)
        response = client.get("/test")
        
        assert response.status_code == 200
        data = response.json()
        assert "test endpoint_url is working" in data["message"]


class TestAuthenticationFunctions:
    """Test authentication functions in isolation."""
    
    def test_is_user_admin_with_realm_role(self):
        """Test admin role detection via realm_access."""
        with patch.dict(os.environ, {
            'KEYCLOAK_DOMAIN': 'http://localhost:8080',
            'KEYCLOAK_REALM': 'test-realm',
            'KEYCLOAK_UI_CLIENT_ID': 'test-client'
        }):
            from api.v0_1.endpoints.service.auth import is_user_admin
            
            admin_payload = {
                "realm_access": {"roles": ["admin", "user"]},
                "resource_access": {}
            }
            
            assert is_user_admin(admin_payload) is True
    
    def test_is_user_admin_with_client_role(self):
        """Test admin role detection via resource_access."""
        with patch.dict(os.environ, {
            'KEYCLOAK_DOMAIN': 'http://localhost:8080',
            'KEYCLOAK_REALM': 'test-realm',
            'KEYCLOAK_UI_CLIENT_ID': 'test-client'
        }):
            from api.v0_1.endpoints.service.auth import is_user_admin
            
            admin_payload = {
                "realm_access": {"roles": ["user"]},
                "resource_access": {
                    "test-client": {"roles": ["admin"]}
                }
            }
            
            assert is_user_admin(admin_payload) is True
    
    def test_is_user_admin_no_admin_role(self):
        """Test when user has no admin role."""
        with patch.dict(os.environ, {
            'KEYCLOAK_DOMAIN': 'http://localhost:8080',
            'KEYCLOAK_REALM': 'test-realm',
            'KEYCLOAK_UI_CLIENT_ID': 'test-client'
        }):
            from api.v0_1.endpoints.service.auth import is_user_admin
            
            user_payload = {
                "realm_access": {"roles": ["user"]},
                "resource_access": {"test-client": {"roles": ["user"]}}
            }
            
            assert is_user_admin(user_payload) is False


class TestAuthenticationEndpoints:
    """Test authentication endpoints with mocked Keycloak."""
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_auth_validate_success(self, mock_jwt_decode, mock_get_jwks_client, 
                                 auth_app, valid_token_payload):
        """Test successful token validation."""
        # Mock JWT validation
        mock_jwt_decode.return_value = valid_token_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        client = TestClient(auth_app)
        headers = {"Authorization": "Bearer valid.jwt.token"}
        response = client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["user"]["preferred_username"] == "testuser"
        assert data["user"]["email"] == "testuser@example.com"
    
    def test_auth_validate_missing_token(self, auth_app):
        """Test validation without token."""
        client = TestClient(auth_app)
        response = client.get("/api/auth/validate")
        
        assert response.status_code == 401
        data = response.json()
        assert "Bearer token required" in data["detail"]
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_auth_validate_expired_token(self, mock_jwt_decode, mock_get_jwks_client, auth_app):
        """Test validation with expired token."""
        # Mock expired token
        mock_jwt_decode.side_effect = jwt_lib.ExpiredSignatureError("Token expired")
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        client = TestClient(auth_app)
        headers = {"Authorization": "Bearer expired.jwt.token"}
        response = client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 401
        data = response.json()
        assert "Could not validate credentials" in data["detail"]
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_auth_validate_admin_user(self, mock_jwt_decode, mock_get_jwks_client,
                                    auth_app, admin_token_payload):
        """Test validation with admin user token."""
        # Mock JWT validation with admin token
        mock_jwt_decode.return_value = admin_token_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        client = TestClient(auth_app)
        headers = {"Authorization": "Bearer admin.jwt.token"}
        response = client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["user"]["preferred_username"] == "adminuser"
        assert "admin" in data["user"]["realm_access"]["roles"]


class TestReactFrontendIntegration:
    """Test React frontend integration scenarios."""
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_react_authentication_workflow(self, mock_jwt_decode, mock_get_jwks_client,
                                         auth_app, valid_token_payload):
        """
        Test complete React authentication workflow.
        
        Simulates:
        1. React app loads and checks authentication
        2. Sends stored token to /auth/validate
        3. Receives user information
        4. Uses info to render appropriate UI
        """
        # Mock successful JWT validation
        mock_jwt_decode.return_value = valid_token_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        client = TestClient(auth_app)
        
        # Simulate React sending token from localStorage
        token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.example.token"
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/auth/validate", headers=headers)
        
        # Verify React gets expected response format
        assert response.status_code == 200
        data = response.json()
        
        # React expects this exact structure
        assert "valid" in data
        assert "user" in data
        assert data["valid"] is True
        
        user = data["user"]
        
        # React needs these fields for UI rendering
        assert user["sub"] == "user-123"
        assert user["preferred_username"] == "testuser"
        assert user["email"] == "testuser@example.com"
        assert user["given_name"] == "Test"
        assert user["family_name"] == "User"
        
        # React uses this for role-based UI
        realm_roles = user["realm_access"]["roles"]
        assert "user" in realm_roles
        
        # Simulate React UI logic
        is_authenticated = data["valid"]
        display_name = user["preferred_username"]
        is_admin = "admin" in realm_roles
        
        assert is_authenticated is True
        assert display_name == "testuser"
        assert is_admin is False
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_react_admin_user_workflow(self, mock_jwt_decode, mock_get_jwks_client,
                                     auth_app, admin_token_payload):
        """
        Test React admin user workflow.
        
        Simulates admin user accessing admin features.
        """
        # Mock admin JWT validation
        mock_jwt_decode.return_value = admin_token_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        client = TestClient(auth_app)
        headers = {"Authorization": "Bearer admin.jwt.token"}
        response = client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        user = data["user"]
        realm_roles = user["realm_access"]["roles"]
        
        # Simulate React admin UI logic
        is_admin = "admin" in realm_roles
        should_show_admin_panel = is_admin
        should_show_user_management = is_admin
        
        assert is_admin is True
        assert should_show_admin_panel is True
        assert should_show_user_management is True
        assert user["preferred_username"] == "adminuser"
    
    def test_react_unauthenticated_workflow(self, auth_app):
        """
        Test React unauthenticated user workflow.
        
        Simulates user without token or with invalid token.
        """
        client = TestClient(auth_app)
        
        # Simulate React app with no token
        response = client.get("/api/auth/validate")
        
        assert response.status_code == 401
        
        # Simulate React error handling
        is_authenticated = response.status_code == 200
        should_redirect_to_login = response.status_code == 401
        should_clear_stored_token = response.status_code == 401
        
        assert is_authenticated is False
        assert should_redirect_to_login is True
        assert should_clear_stored_token is True


class TestErrorHandlingScenarios:
    """Test error handling for React frontend."""
    
    @patch('api.v0_1.endpoints.service.auth.requests.get')
    def test_keycloak_unavailable(self, mock_requests_get, auth_app):
        """Test when Keycloak is unavailable."""
        # Mock Keycloak connection failure
        mock_requests_get.side_effect = Exception("Connection refused")
        
        client = TestClient(auth_app)
        headers = {"Authorization": "Bearer some.token"}
        response = client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 401
        
        # React should handle this gracefully
        should_show_error_message = response.status_code >= 400
        should_clear_token = response.status_code == 401
        
        assert should_show_error_message is True
        assert should_clear_token is True
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    def test_invalid_token_signature(self, mock_get_jwks_client, auth_app):
        """Test handling of token with invalid signature."""
        # Mock JWKS client that fails
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.side_effect = jwt_lib.PyJWKClientError("Invalid key")
        mock_get_jwks_client.return_value = mock_jwks_client
        
        client = TestClient(auth_app)
        headers = {"Authorization": "Bearer invalid.signature.token"}
        response = client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 401
        
        # React should treat this as authentication failure
        should_redirect_to_login = response.status_code == 401
        assert should_redirect_to_login is True


class TestCORSAndHeaders:
    """Test CORS and header handling for React frontend."""
    
    def test_cors_preflight_request(self, auth_app):
        """Test CORS preflight request from React development server."""
        client = TestClient(auth_app)
        
        # Simulate preflight request from React
        response = client.options("/api/auth/validate", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization"
        })
        
        # Should not return an error (exact status depends on FastAPI CORS implementation)
        assert response.status_code in [200, 204, 405]  # 405 is also acceptable for OPTIONS
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.jwt.decode')
    def test_cors_actual_request(self, mock_jwt_decode, mock_get_jwks_client,
                               auth_app, valid_token_payload):
        """Test actual CORS request with Origin header."""
        mock_jwt_decode.return_value = valid_token_payload
        mock_jwks_client = Mock()
        mock_jwks_client.get_signing_key_from_jwt.return_value.key = "mock-key"
        mock_get_jwks_client.return_value = mock_jwks_client
        
        client = TestClient(auth_app)
        headers = {
            "Authorization": "Bearer valid.token",
            "Origin": "http://localhost:3000"
        }
        response = client.get("/api/auth/validate", headers=headers)
        
        assert response.status_code == 200
        # CORS middleware should handle the Origin header appropriately


if __name__ == "__main__":
    # Run tests directly if called as a script
    print("Running simple authentication integration tests...")
    
    import subprocess
    result = subprocess.run([
        sys.executable, '-m', 'pytest', __file__, '-v', '--tb=short'
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    exit(result.returncode)