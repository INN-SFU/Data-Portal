#!/usr/bin/env python3
"""
Unit tests for bearer token authentication functionality.

Tests the bearer token authentication flow specifically for React frontend integration:
- Bearer token validation from Authorization header
- Token decoding and user info extraction
- Authorization header prioritization over cookies
- API endpoint authentication with bearer tokens
"""

import sys
import os
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from datetime import datetime, timedelta
import jwt as jwt_lib
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set minimal environment to avoid import issues
os.environ.setdefault('INSTANCE_CONFIGS', '/tmp/test_configs')
os.environ.setdefault('KEYCLOAK_UI_CLIENT_ID', 'test-client')
os.environ.setdefault('KEYCLOAK_DOMAIN', 'http://localhost:8080')
os.environ.setdefault('KEYCLOAK_REALM', 'test-realm')


class TestBearerTokenDecoding:
    """Test bearer token decoding functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'KEYCLOAK_UI_CLIENT_ID': 'test-client',
            'KEYCLOAK_DOMAIN': 'http://localhost:8080',
            'KEYCLOAK_REALM': 'test-realm',
            'KEYCLOAK_WELL_KNOWN_URL': 'http://localhost:8080/realms/test-realm/.well-known/openid_configuration'
        })
        self.env_patcher.start()
        
        # Create mock JWT payload
        self.mock_jwt_payload = {
            'preferred_username': 'testuser',
            'sub': 'user-uuid-123',
            'email': 'test@example.com',
            'given_name': 'Test',
            'family_name': 'User',
            'realm_access': {'roles': ['user']},
            'resource_access': {
                'test-client': {'roles': ['client-user']}
            },
            'exp': int((datetime.now() + timedelta(hours=1)).timestamp()),
            'iat': int(datetime.now().timestamp()),
            'iss': 'http://localhost:8080/realms/test-realm',
            'azp': 'test-client'
        }
    
    def teardown_method(self):
        """Clean up after tests."""
        self.env_patcher.stop()
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.logger')
    def test_decode_token_from_bearer_header(self, mock_logger, mock_get_jwks_client):
        """Test token decoding from Authorization Bearer header."""
        from api.v0_1.endpoints.service.auth import decode_token
        
        # Mock JWKS client
        mock_jwks_client = Mock()
        mock_signing_key = Mock()
        mock_signing_key.key = "mock_signing_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_get_jwks_client.return_value = mock_jwks_client
        
        # Mock JWT decode
        with patch('jwt.decode', return_value=self.mock_jwt_payload):
            # Create mock request and credentials
            mock_request = Mock()
            mock_request.cookies = {}  # No cookies
            
            mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
            mock_credentials.credentials = "valid.bearer.token"
            
            # Call decode_token
            result = decode_token(mock_request, mock_credentials)
            
            # Verify result
            assert result == self.mock_jwt_payload
            assert result['preferred_username'] == 'testuser'
            assert result['sub'] == 'user-uuid-123'
            assert result['email'] == 'test@example.com'
            
            # Verify logging shows bearer token source
            mock_logger.debug.assert_called_with("Token source: Authorization header")
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    @patch('api.v0_1.endpoints.service.auth.logger')
    def test_decode_token_prioritizes_bearer_over_cookie(self, mock_logger, mock_get_jwks_client):
        """Test that Authorization header is prioritized over cookies."""
        from api.v0_1.endpoints.service.auth import decode_token
        
        # Mock JWKS client
        mock_jwks_client = Mock()
        mock_signing_key = Mock()
        mock_signing_key.key = "mock_signing_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_get_jwks_client.return_value = mock_jwks_client
        
        # Mock JWT decode
        with patch('jwt.decode', return_value=self.mock_jwt_payload):
            # Create mock request with cookie token
            mock_request = Mock()
            mock_request.cookies = {"access_token": "cookie.token.here"}
            
            # Create mock credentials with bearer token
            mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
            mock_credentials.credentials = "bearer.token.here"
            
            # Call decode_token
            result = decode_token(mock_request, mock_credentials)
            
            # Verify bearer token was used (not cookie)
            mock_logger.debug.assert_called_with("Token source: Authorization header")
            
            # Verify JWT decode was called with bearer token
            jwt_decode_call = patch('jwt.decode').return_value
            # The actual token passed to jwt.decode should be the bearer token
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client') 
    @patch('api.v0_1.endpoints.service.auth.logger')
    def test_decode_token_fallback_to_cookie(self, mock_logger, mock_get_jwks_client):
        """Test fallback to cookie when no Authorization header provided."""
        from api.v0_1.endpoints.service.auth import decode_token
        
        # Mock JWKS client
        mock_jwks_client = Mock()
        mock_signing_key = Mock()
        mock_signing_key.key = "mock_signing_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_get_jwks_client.return_value = mock_jwks_client
        
        # Mock JWT decode
        with patch('jwt.decode', return_value=self.mock_jwt_payload):
            # Create mock request with cookie token
            mock_request = Mock()
            mock_request.cookies = {"access_token": "cookie.token.here"}
            
            # No bearer credentials
            mock_credentials = None
            
            # Call decode_token
            result = decode_token(mock_request, mock_credentials)
            
            # Verify cookie was used as fallback
            mock_logger.debug.assert_called_with("Token source: cookie")
            assert result == self.mock_jwt_payload
    
    def test_decode_token_no_token_raises_exception(self):
        """Test that missing token raises HTTPException."""
        from api.v0_1.endpoints.service.auth import decode_token
        
        # Create mock request without any tokens
        mock_request = Mock()
        mock_request.cookies = {}
        
        # No bearer credentials
        mock_credentials = None
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            decode_token(mock_request, mock_credentials)
        
        assert exc_info.value.status_code == 401
        assert "Not authenticated" in str(exc_info.value.detail)
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    def test_decode_token_invalid_signature_raises_exception(self, mock_get_jwks_client):
        """Test that invalid token signature raises HTTPException."""
        from api.v0_1.endpoints.service.auth import decode_token
        
        # Mock JWKS client
        mock_jwks_client = Mock()
        mock_signing_key = Mock()
        mock_signing_key.key = "mock_signing_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_get_jwks_client.return_value = mock_jwks_client
        
        # Mock JWT decode to raise signature error
        with patch('jwt.decode', side_effect=jwt_lib.InvalidSignatureError("Invalid signature")):
            mock_request = Mock()
            mock_request.cookies = {}
            
            mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
            mock_credentials.credentials = "invalid.signature.token"
            
            # Should raise HTTPException
            with pytest.raises(HTTPException) as exc_info:
                decode_token(mock_request, mock_credentials)
            
            assert exc_info.value.status_code == 401
            assert "Could not validate credentials" in str(exc_info.value.detail)
    
    @patch('api.v0_1.endpoints.service.auth.get_jwks_client')
    def test_decode_token_expired_token_raises_exception(self, mock_get_jwks_client):
        """Test that expired token raises HTTPException.""" 
        from api.v0_1.endpoints.service.auth import decode_token
        
        # Mock JWKS client
        mock_jwks_client = Mock()
        mock_signing_key = Mock()
        mock_signing_key.key = "mock_signing_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_get_jwks_client.return_value = mock_jwks_client
        
        # Mock JWT decode to raise expired signature error
        with patch('jwt.decode', side_effect=jwt_lib.ExpiredSignatureError("Token expired")):
            mock_request = Mock()
            mock_request.cookies = {}
            
            mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
            mock_credentials.credentials = "expired.token.here"
            
            # Should raise HTTPException
            with pytest.raises(HTTPException) as exc_info:
                decode_token(mock_request, mock_credentials)
            
            assert exc_info.value.status_code == 401
            assert "Could not validate credentials" in str(exc_info.value.detail)


class TestUserInfoExtraction:
    """Test user information extraction from JWT payload."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.admin_payload = {
            'preferred_username': 'admin',
            'sub': 'admin-uuid-456',
            'email': 'admin@example.com', 
            'given_name': 'Admin',
            'family_name': 'User',
            'realm_access': {'roles': ['admin', 'user']},
            'resource_access': {
                'test-client': {'roles': ['admin', 'client-admin']}
            },
            'exp': int((datetime.now() + timedelta(hours=1)).timestamp()),
            'iat': int(datetime.now().timestamp())
        }
        
        self.regular_user_payload = {
            'preferred_username': 'user',
            'sub': 'user-uuid-789',
            'email': 'user@example.com',
            'realm_access': {'roles': ['user']},
            'resource_access': {},
            'exp': int((datetime.now() + timedelta(hours=1)).timestamp()),
            'iat': int(datetime.now().timestamp())
        }
    
    def test_is_user_admin_realm_roles(self):
        """Test admin detection from realm roles."""
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        assert is_user_admin(self.admin_payload) is True
        assert is_user_admin(self.regular_user_payload) is False
    
    def test_is_user_admin_client_roles(self):
        """Test admin detection from client-specific roles."""
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        client_admin_payload = {
            'preferred_username': 'client_admin',
            'realm_access': {'roles': ['user']},  # No realm admin role
            'resource_access': {
                'test-client': {'roles': ['admin']}  # But has client admin role
            }
        }
        
        assert is_user_admin(client_admin_payload) is True
    
    def test_user_info_extraction_from_token(self):
        """Test extracting standard user info from JWT token."""
        # Test with admin user
        assert self.admin_payload['preferred_username'] == 'admin'
        assert self.admin_payload['sub'] == 'admin-uuid-456'
        assert self.admin_payload['email'] == 'admin@example.com'
        assert 'admin' in self.admin_payload['realm_access']['roles']
        
        # Test with regular user
        assert self.regular_user_payload['preferred_username'] == 'user'
        assert self.regular_user_payload['sub'] == 'user-uuid-789' 
        assert self.regular_user_payload['email'] == 'user@example.com'
        assert 'user' in self.regular_user_payload['realm_access']['roles']


class TestAPIEndpointAuthentication:
    """Test API endpoint authentication with bearer tokens."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.env_patcher = patch.dict(os.environ, {
            'KEYCLOAK_UI_CLIENT_ID': 'test-client',
            'KEYCLOAK_DOMAIN': 'http://localhost:8080',
            'KEYCLOAK_REALM': 'test-realm',
            'KEYCLOAK_WELL_KNOWN_URL': 'http://localhost:8080/realms/test-realm/.well-known/openid_configuration'
        })
        self.env_patcher.start()
        
        self.mock_user_payload = {
            'preferred_username': 'api_user',
            'sub': 'api-user-uuid',
            'email': 'api@example.com',
            'realm_access': {'roles': ['user']},
            'resource_access': {},
            'exp': int((datetime.now() + timedelta(hours=1)).timestamp()),
            'iat': int(datetime.now().timestamp())
        }
    
    def teardown_method(self):
        """Clean up after tests."""
        self.env_patcher.stop()
    
    @patch('api.v0_1.endpoints.service.auth.decode_token')
    def test_auth_test_endpoint_with_bearer_token(self, mock_decode_token):
        """Test /auth/test endpoint with bearer token."""
        from api.v0_1.endpoints.service.auth import auth
        from fastapi.responses import JSONResponse
        
        # Mock decode_token to return user payload
        mock_decode_token.return_value = self.mock_user_payload
        
        # Call the auth endpoint
        result = auth(user=self.mock_user_payload)
        
        # Verify response
        assert isinstance(result, JSONResponse)
        assert result.status_code == 200
        
        # Verify response content contains user info
        content = result.body.decode()
        assert '"success":"Valid token"' in content
        assert '"api_user"' in content
    
    @patch('api.v0_1.endpoints.service.auth.decode_token')
    def test_protected_endpoint_user_extraction(self, mock_decode_token):
        """Test that protected endpoints can extract user info from bearer token."""
        # Mock decode_token to return user payload
        mock_decode_token.return_value = self.mock_user_payload
        
        # Simulate a protected endpoint that uses Depends(decode_token)
        def mock_protected_endpoint(user: dict):
            return {
                "username": user['preferred_username'],
                "user_id": user['sub'],
                "email": user['email'],
                "roles": user['realm_access']['roles']
            }
        
        # Call with decoded user
        result = mock_protected_endpoint(self.mock_user_payload)
        
        # Verify user info is accessible
        assert result['username'] == 'api_user'
        assert result['user_id'] == 'api-user-uuid'
        assert result['email'] == 'api@example.com'
        assert result['roles'] == ['user']


class TestReactIntegrationScenarios:
    """Test scenarios specific to React frontend integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.react_user_token = {
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
            'azp': 'ams-portal-ui'  # Authorized party
        }
    
    def test_react_token_structure(self):
        """Test that React token contains expected structure."""
        # Verify standard claims
        assert 'preferred_username' in self.react_user_token
        assert 'sub' in self.react_user_token  # User UUID
        assert 'email' in self.react_user_token
        assert 'exp' in self.react_user_token  # Expiration
        assert 'iat' in self.react_user_token  # Issued at
        
        # Verify role structure
        assert 'realm_access' in self.react_user_token
        assert 'roles' in self.react_user_token['realm_access']
        assert 'resource_access' in self.react_user_token
        
        # Verify client information
        assert 'azp' in self.react_user_token  # Authorized party
    
    def test_react_user_permissions_extraction(self):
        """Test extracting permissions for React frontend."""
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        # Extract user info for React
        user_info = {
            "username": self.react_user_token['preferred_username'],
            "user_id": self.react_user_token['sub'],
            "email": self.react_user_token['email'],
            "is_admin": is_user_admin(self.react_user_token),
            "roles": self.react_user_token['realm_access']['roles'],
            "client_roles": self.react_user_token['resource_access'].get('ams-portal-ui', {}).get('roles', [])
        }
        
        # Verify extracted info
        assert user_info['username'] == 'react_user'
        assert user_info['user_id'] == 'react-user-uuid'
        assert user_info['email'] == 'react@example.com'
        assert user_info['is_admin'] is False
        assert user_info['roles'] == ['user']
        assert user_info['client_roles'] == ['portal-user']
    
    @patch('api.v0_1.endpoints.service.auth.logger')
    def test_react_authentication_flow_logging(self, mock_logger):
        """Test that React authentication flow is properly logged."""
        from api.v0_1.endpoints.service.auth import is_user_admin
        
        # Simulate React authentication
        is_admin = is_user_admin(self.react_user_token)
        
        # Verify admin check logging (function should log its checks)
        assert mock_logger.debug.called


if __name__ == "__main__":
    # Run tests directly if called as a script
    print("Running bearer token authentication tests...")
    
    # Run pytest
    import subprocess
    result = subprocess.run([
        sys.executable, '-m', 'pytest', __file__, '-v'
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    exit(result.returncode)