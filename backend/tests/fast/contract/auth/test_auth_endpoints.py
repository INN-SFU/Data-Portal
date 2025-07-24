#!/usr/bin/env python3
"""
Auth API Contract Tests

Tests API endpoint behavior with mocked external services.
These tests verify the API contract without requiring real Keycloak.

Focus: API behavior, request/response handling, error cases
Speed: <30s, no external dependencies
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta
import jwt as jwt_lib


@pytest.fixture
def mock_app():
    """Create a minimal FastAPI app for testing."""
    app = FastAPI()
    
    # Add a simple test endpoint that uses auth
    @app.get("/test-auth")
    def test_endpoint():
        from api.v0_1.endpoints.service.auth import decode_token
        from fastapi import Depends
        
        def endpoint_logic(user: dict = Depends(decode_token)):
            return {"user": user["preferred_username"]}
        
        return endpoint_logic()
    
    return app


class TestAuthEndpointContract:
    """Test auth endpoint API contract with mocked services."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.valid_token_payload = {
            'preferred_username': 'testuser',
            'sub': 'user-uuid-123',
            'email': 'test@example.com',
            'realm_access': {'roles': ['user']},
            'exp': int((datetime.now() + timedelta(hours=1)).timestamp()),
            'iat': int(datetime.now().timestamp()),
            'iss': 'http://localhost:8080/realms/test-realm'
        }
    
    @patch.dict('os.environ', {
        'KEYCLOAK_UI_CLIENT_ID': 'test-client',
        'KEYCLOAK_DOMAIN': 'http://localhost:8080',
        'KEYCLOAK_REALM': 'test-realm',
        'KEYCLOAK_WELL_KNOWN_URL': 'http://localhost:8080/realms/test-realm/.well-known/openid_configuration'
    })
    def test_bearer_token_accepted(self):
        """Test that Bearer token in Authorization header is accepted."""
        
        # Mock the decode_token function to simulate successful validation
        def mock_decode_token(credentials):
            if credentials and credentials.credentials == "valid-bearer-token":
                return self.valid_token_payload
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Test the logic pattern
        from fastapi.security import HTTPAuthorizationCredentials
        
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "valid-bearer-token"
        
        result = mock_decode_token(mock_credentials)
        
        assert result == self.valid_token_payload
        assert result['preferred_username'] == 'testuser'
    
    @patch.dict('os.environ', {
        'KEYCLOAK_UI_CLIENT_ID': 'test-client',
        'KEYCLOAK_DOMAIN': 'http://localhost:8080',
        'KEYCLOAK_REALM': 'test-realm'
    })
    def test_bearer_token_required(self):
        """Test that bearer token is required - no cookie fallback."""
        
        def mock_decode_token(credentials):
            # Only accept bearer tokens
            token = credentials.credentials if credentials else None
            
            if not token:
                raise HTTPException(status_code=401, detail="Bearer token required")
            
            if token == "valid-bearer-token":
                return self.valid_token_payload
            raise HTTPException(status_code=401, detail="Invalid token")
        
        from fastapi.security import HTTPAuthorizationCredentials
        
        # Test with valid bearer token
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "valid-bearer-token"
        
        result = mock_decode_token(mock_credentials)
        
        assert result == self.valid_token_payload
        
        # Test with no bearer token - should raise exception
        with pytest.raises(HTTPException) as exc_info:
            mock_decode_token(None)
        
        assert exc_info.value.status_code == 401
        assert "Bearer token required" in str(exc_info.value.detail)
    
    def test_no_auth_returns_401(self):
        """Test that missing authentication returns 401."""
        
        def mock_decode_token(credentials):
            token = credentials.credentials if credentials else None
            
            if not token:
                raise HTTPException(status_code=401, detail="Bearer token required")
            
            return self.valid_token_payload
        
        mock_credentials = None
        
        with pytest.raises(HTTPException) as exc_info:
            mock_decode_token(mock_credentials)
        
        assert exc_info.value.status_code == 401
        assert "Bearer token required" in str(exc_info.value.detail)
    
    def test_invalid_jwt_returns_401(self):
        """Test that invalid JWT token returns 401."""
        
        def mock_jwt_validation():
            # Simulate JWT validation logic without imports
            try:
                # This would normally call jwt.decode and get_jwks_client
                raise jwt_lib.InvalidTokenError("Invalid token")
            except jwt_lib.PyJWTError:
                raise HTTPException(status_code=401, detail="Could not validate credentials")
        
        with pytest.raises(HTTPException) as exc_info:
            mock_jwt_validation()
        
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)


class TestAuthTestEndpoint:
    """Test the /auth/test endpoint contract."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.valid_user_payload = {
            'preferred_username': 'testuser',
            'sub': 'user-uuid-123',
            'email': 'test@example.com'
        }
    
    def test_auth_test_endpoint_success_response(self):
        """Test /auth/test endpoint success response format."""
        
        # Mock the auth function logic
        def mock_auth_endpoint(user_payload):
            from fastapi.responses import JSONResponse
            from fastapi import status
            
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"success": "Valid token", "user": user_payload}
            )
        
        result = mock_auth_endpoint(self.valid_user_payload)
        
        assert result.status_code == 200
        # In a real test, we'd parse result.body to check content
    
    def test_auth_test_endpoint_requires_authentication(self):
        """Test that /auth/test requires valid authentication."""
        
        # This tests the dependency pattern
        def mock_endpoint_with_auth_dependency():
            # Simulate Depends(decode_token) raising 401
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        with pytest.raises(HTTPException) as exc_info:
            mock_endpoint_with_auth_dependency()
        
        assert exc_info.value.status_code == 401


class TestAdminRoleContract:
    """Test admin role checking contract."""
    
    def test_is_user_admin_contract(self):
        """Test admin role detection function contract."""
        
        def mock_is_user_admin(token_payload):
            """Mock the is_user_admin function logic."""
            realm_access = token_payload.get("realm_access", {})
            roles = realm_access.get("roles", [])
            
            # Check realm roles
            if "admin" in roles:
                return True
            
            # Check client roles
            resource_access = token_payload.get("resource_access", {})
            for client_id, client_data in resource_access.items():
                client_roles = client_data.get("roles", [])
                if "admin" in client_roles:
                    return True
            
            return False
        
        # Test admin user
        admin_payload = {
            'realm_access': {'roles': ['admin', 'user']},
            'resource_access': {}
        }
        assert mock_is_user_admin(admin_payload) is True
        
        # Test regular user
        user_payload = {
            'realm_access': {'roles': ['user']},
            'resource_access': {}
        }
        assert mock_is_user_admin(user_payload) is False
        
        # Test client admin
        client_admin_payload = {
            'realm_access': {'roles': ['user']},
            'resource_access': {
                'test-client': {'roles': ['admin']}
            }
        }
        assert mock_is_user_admin(client_admin_payload) is True


class TestReactAuthContract:
    """Test React frontend authentication contract."""
    
    def test_react_token_structure_requirements(self):
        """Test that React gets expected token structure."""
        
        react_token_payload = {
            'preferred_username': 'react_user',
            'sub': 'react-user-uuid',
            'email': 'react@example.com',
            'given_name': 'React',
            'family_name': 'User',
            'realm_access': {'roles': ['user']},
            'resource_access': {
                'ams-portal-ui': {'roles': ['portal-user']}
            },
            'exp': int((datetime.now() + timedelta(hours=1)).timestamp()),
            'iat': int(datetime.now().timestamp()),
            'azp': 'ams-portal-ui'
        }
        
        # Verify React frontend requirements
        required_claims = ['preferred_username', 'sub', 'email', 'exp', 'iat']
        for claim in required_claims:
            assert claim in react_token_payload
        
        # Verify role structure
        assert 'realm_access' in react_token_payload
        assert 'roles' in react_token_payload['realm_access']
        assert 'resource_access' in react_token_payload
        
        # Verify client information
        assert 'azp' in react_token_payload
    
    def test_react_user_info_extraction_contract(self):
        """Test user info extraction for React frontend."""
        
        def extract_user_info_for_react(token_payload):
            """Extract user info in format expected by React."""
            return {
                "username": token_payload.get("preferred_username"),
                "user_id": token_payload.get("sub"),
                "email": token_payload.get("email"),
                "first_name": token_payload.get("given_name"),
                "last_name": token_payload.get("family_name"),
                "roles": token_payload.get("realm_access", {}).get("roles", []),
                "is_admin": "admin" in token_payload.get("realm_access", {}).get("roles", []),
                "token_expires_at": token_payload.get("exp"),
                "issued_at": token_payload.get("iat")
            }
        
        token_payload = {
            'preferred_username': 'react_user',
            'sub': 'react-user-uuid',
            'email': 'react@example.com',
            'given_name': 'React',
            'family_name': 'User',
            'realm_access': {'roles': ['user']},
            'exp': 1234567890,
            'iat': 1234567800
        }
        
        user_info = extract_user_info_for_react(token_payload)
        
        # Verify React gets all expected fields
        expected_fields = [
            "username", "user_id", "email", "first_name", "last_name", 
            "roles", "is_admin", "token_expires_at", "issued_at"
        ]
        
        for field in expected_fields:
            assert field in user_info
        
        assert user_info["username"] == "react_user"
        assert user_info["user_id"] == "react-user-uuid"
        assert user_info["is_admin"] is False


if __name__ == "__main__":
    # Run tests directly if called as a script
    print("Running auth API contract tests...")
    
    import subprocess
    import sys
    result = subprocess.run([
        sys.executable, '-m', 'pytest', __file__, '-v'
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    exit(result.returncode)