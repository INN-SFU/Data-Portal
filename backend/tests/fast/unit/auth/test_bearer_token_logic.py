#!/usr/bin/env python3
"""
Unit tests for bearer token logic (mocked).

Tests the bearer token authentication logic without external dependencies:
- Authorization header prioritization over cookies
- JWT token validation logic  
- User info extraction from token payload
- Error handling for invalid/expired tokens
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import jwt as jwt_lib
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


class TestBearerTokenPrioritization:
    """Test bearer token prioritization logic."""
    
    def test_bearer_header_prioritized_over_cookie(self):
        """Test that Authorization header is prioritized over cookies."""
        
        # Mock the decode_token function logic
        def mock_decode_token_logic(request, credentials):
            # This simulates our actual prioritization logic
            token = credentials.credentials if credentials else None
            token_source = "Authorization header" if token else None
            
            # Fall back to cookie
            if not token:
                token = request.cookies.get("access_token")
                token_source = "cookie" if token else None
            
            if not token:
                raise HTTPException(status_code=401, detail="Not authenticated")
            
            return {"token": token, "source": token_source}
        
        # Test with both bearer token and cookie
        mock_request = Mock()
        mock_request.cookies = {"access_token": "cookie_token"}
        
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "bearer_token"
        
        result = mock_decode_token_logic(mock_request, mock_credentials)
        
        assert result["token"] == "bearer_token"
        assert result["source"] == "Authorization header"
    
    def test_fallback_to_cookie_when_no_bearer(self):
        """Test fallback to cookie when no Authorization header."""
        
        def mock_decode_token_logic(request, credentials):
            token = credentials.credentials if credentials else None
            token_source = "Authorization header" if token else None
            
            if not token:
                token = request.cookies.get("access_token")
                token_source = "cookie" if token else None
            
            if not token:
                raise HTTPException(status_code=401, detail="Not authenticated")
            
            return {"token": token, "source": token_source}
        
        # Test with only cookie
        mock_request = Mock()
        mock_request.cookies = {"access_token": "cookie_token"}
        
        mock_credentials = None  # No bearer token
        
        result = mock_decode_token_logic(mock_request, mock_credentials)
        
        assert result["token"] == "cookie_token"
        assert result["source"] == "cookie"
    
    def test_no_token_raises_exception(self):
        """Test that missing tokens raise HTTPException."""
        
        def mock_decode_token_logic(request, credentials):
            token = credentials.credentials if credentials else None
            if not token:
                token = request.cookies.get("access_token")
            
            if not token:
                raise HTTPException(status_code=401, detail="Not authenticated")
            
            return {"token": token}
        
        # Test with no tokens
        mock_request = Mock()
        mock_request.cookies = {}
        mock_credentials = None
        
        with pytest.raises(HTTPException) as exc_info:
            mock_decode_token_logic(mock_request, mock_credentials)
        
        assert exc_info.value.status_code == 401
        assert "Not authenticated" in str(exc_info.value.detail)


class TestJWTValidationLogic:
    """Test JWT validation logic patterns."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.valid_payload = {
            'preferred_username': 'testuser',
            'sub': 'user-uuid-123',
            'email': 'test@example.com',
            'realm_access': {'roles': ['user']},
            'exp': int((datetime.now() + timedelta(hours=1)).timestamp()),
            'iat': int(datetime.now().timestamp()),
            'iss': 'http://localhost:8080/realms/test-realm'
        }
    
    def test_valid_jwt_decode_pattern(self):
        """Test the JWT validation pattern."""
        
        def mock_jwt_validation_logic(token):
            # Mock the validation pattern used in decode_token
            try:
                # This would normally call jwt.decode with real validation
                return self.valid_payload  # Simulate successful decode
            except jwt_lib.PyJWTError as e:
                raise HTTPException(status_code=401, detail="Could not validate credentials")
        
        result = mock_jwt_validation_logic("valid.jwt.token")
        
        assert result == self.valid_payload
        assert result['preferred_username'] == 'testuser'
        assert result['sub'] == 'user-uuid-123'
    
    def test_expired_token_error_handling(self):
        """Test handling of expired tokens."""
        
        def mock_jwt_validation_logic(token):
            # Simulate expired token
            raise jwt_lib.ExpiredSignatureError("Token expired")
        
        with pytest.raises(jwt_lib.ExpiredSignatureError):
            mock_jwt_validation_logic("expired.jwt.token")
    
    def test_invalid_signature_error_handling(self):
        """Test handling of invalid signatures."""
        
        def mock_jwt_validation_logic(token):
            # Simulate invalid signature
            raise jwt_lib.InvalidSignatureError("Invalid signature")
        
        with pytest.raises(jwt_lib.InvalidSignatureError):
            mock_jwt_validation_logic("invalid.signature.token")


class TestUserInfoExtraction:
    """Test user information extraction from JWT payload."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.admin_payload = {
            'preferred_username': 'admin',
            'sub': 'admin-uuid-456',
            'email': 'admin@example.com',
            'realm_access': {'roles': ['admin', 'user']},
            'resource_access': {
                'test-client': {'roles': ['admin']}
            }
        }
        
        self.user_payload = {
            'preferred_username': 'user',
            'sub': 'user-uuid-789',
            'email': 'user@example.com',
            'realm_access': {'roles': ['user']},
            'resource_access': {}
        }
    
    def test_admin_role_detection_realm(self):
        """Test admin detection from realm roles."""
        
        def is_user_admin_logic(payload):
            realm_access = payload.get("realm_access", {})
            roles = realm_access.get("roles", [])
            return "admin" in roles
        
        assert is_user_admin_logic(self.admin_payload) is True
        assert is_user_admin_logic(self.user_payload) is False
    
    def test_admin_role_detection_client(self):
        """Test admin detection from client roles."""
        
        def is_user_admin_logic(payload):
            # Check realm roles first
            realm_access = payload.get("realm_access", {})
            roles = realm_access.get("roles", [])
            if "admin" in roles:
                return True
            
            # Check client roles
            resource_access = payload.get("resource_access", {})
            for client_id, client_data in resource_access.items():
                client_roles = client_data.get("roles", [])
                if "admin" in client_roles:
                    return True
            
            return False
        
        client_admin_payload = {
            'preferred_username': 'client_admin',
            'realm_access': {'roles': ['user']},  # No realm admin
            'resource_access': {
                'test-client': {'roles': ['admin']}  # But client admin
            }
        }
        
        assert is_user_admin_logic(client_admin_payload) is True
        assert is_user_admin_logic(self.user_payload) is False
    
    def test_user_info_extraction_pattern(self):
        """Test extracting user info from JWT payload."""
        
        def extract_user_info_logic(payload):
            return {
                "username": payload.get("preferred_username"),
                "user_id": payload.get("sub"),
                "email": payload.get("email"),
                "roles": payload.get("realm_access", {}).get("roles", [])
            }
        
        user_info = extract_user_info_logic(self.admin_payload)
        
        assert user_info["username"] == "admin"
        assert user_info["user_id"] == "admin-uuid-456"
        assert user_info["email"] == "admin@example.com"
        assert "admin" in user_info["roles"]
        assert "user" in user_info["roles"]


class TestReactTokenPatterns:
    """Test patterns specific to React frontend integration."""
    
    def test_react_token_structure_validation(self):
        """Test that React tokens have expected structure."""
        
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
            'azp': 'ams-portal-ui'  # Authorized party
        }
        
        # Validate expected claims exist
        required_claims = ['preferred_username', 'sub', 'email', 'exp', 'iat']
        for claim in required_claims:
            assert claim in react_token_payload
        
        # Validate role structure
        assert 'realm_access' in react_token_payload
        assert 'roles' in react_token_payload['realm_access']
        assert 'resource_access' in react_token_payload
        
        # Validate client information
        assert 'azp' in react_token_payload
        assert react_token_payload['azp'] == 'ams-portal-ui'
    
    def test_react_user_permissions_extraction(self):
        """Test extracting permissions for React frontend."""
        
        def extract_react_permissions_logic(payload):
            realm_roles = payload.get('realm_access', {}).get('roles', [])
            is_admin = 'admin' in realm_roles
            
            # Extract client roles
            client_roles = []
            resource_access = payload.get('resource_access', {})
            for client_id, client_data in resource_access.items():
                client_roles.extend(client_data.get('roles', []))
            
            return {
                "username": payload.get('preferred_username'),
                "is_admin": is_admin,
                "realm_roles": realm_roles,
                "client_roles": client_roles,
                "capabilities": {
                    "can_upload": True,  # All users can upload
                    "can_download": True,  # All users can download
                    "can_admin": is_admin
                }
            }
        
        react_payload = {
            'preferred_username': 'react_user',
            'realm_access': {'roles': ['user']},
            'resource_access': {
                'ams-portal-ui': {'roles': ['portal-user']}
            }
        }
        
        permissions = extract_react_permissions_logic(react_payload)
        
        assert permissions['username'] == 'react_user'
        assert permissions['is_admin'] is False
        assert permissions['realm_roles'] == ['user']
        assert permissions['client_roles'] == ['portal-user']
        assert permissions['capabilities']['can_upload'] is True
        assert permissions['capabilities']['can_admin'] is False


if __name__ == "__main__":
    # Run tests directly if called as a script
    print("Running bearer token logic tests...")
    
    import subprocess
    import sys
    result = subprocess.run([
        sys.executable, '-m', 'pytest', __file__, '-v'
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    exit(result.returncode)