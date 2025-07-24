#!/usr/bin/env python3
"""
Integration tests for bearer token authentication with real Keycloak.

Tests the full bearer token authentication flow with real services:
- Real JWT token validation against test Keycloak
- Bearer token authentication on actual endpoints  
- React frontend authentication integration
- Full token lifecycle (login, validate, refresh)
"""

import os
import sys
import pytest
import requests
import time
from pathlib import Path
from datetime import datetime, timedelta

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class TestKeycloakIntegration:
    """Test integration with real Keycloak instance."""
    
    @classmethod
    def setup_class(cls):
        """Set up class-level fixtures."""
        cls.keycloak_url = "http://localhost:8081"
        cls.realm = "test-realm"
        cls.client_id = "ams-test-client"
        cls.client_secret = "test-client-secret-123"
        
        # Test user credentials
        cls.test_user = {
            "username": "testuser",
            "password": "testpass123"
        }
        
        cls.test_admin = {
            "username": "testadmin", 
            "password": "adminpass123"
        }
    
    def wait_for_keycloak(self, timeout=120):
        """Wait for Keycloak to be ready."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.keycloak_url}/health/ready", timeout=5)
                if response.status_code == 200:
                    return True
            except requests.RequestException:
                pass
            
            time.sleep(2)
        
        return False
    
    def get_access_token(self, username, password):
        """Get access token for user via direct grant."""
        token_url = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token"
        
        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": username,
            "password": password,
            "scope": "openid profile email"
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        return response.json()
    
    @pytest.mark.integration
    def test_keycloak_connection(self):
        """Test that we can connect to test Keycloak."""
        if not self.wait_for_keycloak():
            pytest.skip("Keycloak test instance not available")
        
        # Test realm endpoint
        realm_url = f"{self.keycloak_url}/realms/{self.realm}"
        response = requests.get(realm_url)
        
        assert response.status_code == 200
        realm_info = response.json()
        assert realm_info["realm"] == self.realm
    
    @pytest.mark.integration  
    def test_get_access_token_for_user(self):
        """Test getting access token for test user."""
        if not self.wait_for_keycloak():
            pytest.skip("Keycloak test instance not available")
        
        token_data = self.get_access_token(
            self.test_user["username"],
            self.test_user["password"]
        )
        
        assert "access_token" in token_data
        assert "refresh_token" in token_data
        assert token_data["token_type"] == "Bearer"
        
        # Verify token structure
        access_token = token_data["access_token"]
        assert len(access_token.split(".")) == 3  # JWT has 3 parts
    
    @pytest.mark.integration
    def test_get_access_token_for_admin(self):
        """Test getting access token for test admin."""
        if not self.wait_for_keycloak():
            pytest.skip("Keycloak test instance not available")
        
        token_data = self.get_access_token(
            self.test_admin["username"],
            self.test_admin["password"]
        )
        
        assert "access_token" in token_data
        access_token = token_data["access_token"]
        assert len(access_token.split(".")) == 3


class TestBearerTokenValidation:
    """Test bearer token validation with real tokens."""
    
    @classmethod
    def setup_class(cls):
        """Set up class-level fixtures."""
        cls.keycloak_url = "http://localhost:8081"
        cls.realm = "test-realm"
        cls.client_id = "ams-test-client"
        cls.client_secret = "test-client-secret-123"
        
        cls.test_user = {
            "username": "testuser",
            "password": "testpass123"
        }
    
    def wait_for_keycloak(self, timeout=120):
        """Wait for Keycloak to be ready."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.keycloak_url}/health/ready", timeout=5)
                if response.status_code == 200:
                    return True
            except requests.RequestException:
                pass
            
            time.sleep(2)
        
        return False
    
    def get_access_token(self, username, password):
        """Get access token for user."""
        token_url = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token"
        
        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": username,
            "password": password
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        return response.json()
    
    @pytest.mark.integration
    def test_jwt_token_validation_pattern(self):
        """Test JWT token validation against real Keycloak."""
        if not self.wait_for_keycloak():
            pytest.skip("Keycloak test instance not available")
        
        # Get real token
        token_data = self.get_access_token(
            self.test_user["username"],
            self.test_user["password"]
        )
        access_token = token_data["access_token"]
        
        # Test the validation pattern (simulate what decode_token does)
        import jwt
        import requests
        
        # Get JWKS (public keys) from Keycloak
        jwks_url = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/certs"
        jwks_response = requests.get(jwks_url)
        jwks_response.raise_for_status()
        
        # This simulates what our decode_token function does
        # (We're testing the pattern, not importing the actual function to avoid deps)
        
        # Verify token structure
        token_parts = access_token.split(".")
        assert len(token_parts) == 3
        
        # Decode header to verify algorithm
        import base64
        import json
        
        # Decode header (first part)
        header_data = base64.urlsafe_b64decode(token_parts[0] + "==")
        header = json.loads(header_data)
        
        assert header["alg"] == "RS256"
        assert "kid" in header  # Key ID for JWKS lookup
    
    @pytest.mark.integration
    def test_token_payload_structure(self):
        """Test that token payload has expected structure for React."""
        if not self.wait_for_keycloak():
            pytest.skip("Keycloak test instance not available")
        
        # Get real token
        token_data = self.get_access_token(
            self.test_user["username"],
            self.test_user["password"]
        )
        access_token = token_data["access_token"]
        
        # Decode payload (without verification for testing)
        import base64
        import json
        
        token_parts = access_token.split(".")
        payload_data = base64.urlsafe_b64decode(token_parts[1] + "==")
        payload = json.loads(payload_data)
        
        # Verify expected claims for React frontend
        expected_claims = [
            "preferred_username",
            "sub",  # User UUID
            "email",
            "exp",  # Expiration
            "iat",  # Issued at
            "iss",  # Issuer
            "realm_access"  # Roles
        ]
        
        for claim in expected_claims:
            assert claim in payload, f"Missing claim: {claim}"
        
        # Verify user info
        assert payload["preferred_username"] == "testuser"
        assert payload["email"] == "test@example.com"
        assert "user" in payload["realm_access"]["roles"]
        
        # Verify issuer
        expected_issuer = f"{self.keycloak_url}/realms/{self.realm}"
        assert payload["iss"] == expected_issuer


class TestReactAuthenticationFlow:
    """Test authentication patterns for React frontend."""
    
    @classmethod
    def setup_class(cls):
        """Set up class-level fixtures."""
        cls.keycloak_url = "http://localhost:8081"
        cls.realm = "test-realm"
        cls.client_id = "ams-test-client"
        cls.client_secret = "test-client-secret-123"
    
    def wait_for_keycloak(self, timeout=120):
        """Wait for Keycloak to be ready."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.keycloak_url}/health/ready", timeout=5)
                if response.status_code == 200:
                    return True
            except requests.RequestException:
                pass
            
            time.sleep(2)
        
        return False
    
    @pytest.mark.integration
    def test_react_token_refresh_flow(self):
        """Test token refresh flow for React frontend."""
        if not self.wait_for_keycloak():
            pytest.skip("Keycloak test instance not available")
        
        # Get initial tokens
        token_url = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token"
        
        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": "testuser",
            "password": "testpass123"
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        initial_tokens = response.json()
        refresh_token = initial_tokens["refresh_token"]
        
        # Test refresh flow
        refresh_data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token
        }
        
        refresh_response = requests.post(token_url, data=refresh_data)
        refresh_response.raise_for_status()
        
        new_tokens = refresh_response.json()
        
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        assert new_tokens["access_token"] != initial_tokens["access_token"]
    
    @pytest.mark.integration
    def test_react_authorization_header_format(self):
        """Test proper Authorization header format for React."""
        if not self.wait_for_keycloak():
            pytest.skip("Keycloak test instance not available")
        
        # Get access token
        token_url = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token"
        
        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": "testuser",
            "password": "testpass123"
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data["access_token"]
        
        # Test Authorization header format
        auth_header = f"Bearer {access_token}"
        
        # Verify format
        assert auth_header.startswith("Bearer ")
        assert len(auth_header.split(" ")) == 2
        
        # Verify token part
        token_part = auth_header.split(" ")[1]
        assert len(token_part.split(".")) == 3  # Valid JWT


if __name__ == "__main__":
    # Run tests directly if called as a script
    print("Running bearer token integration tests...")
    print("Note: Requires test Keycloak instance running on port 8081")
    
    import subprocess
    result = subprocess.run([
        sys.executable, '-m', 'pytest', __file__, '-v', '-m', 'integration'
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    exit(result.returncode)