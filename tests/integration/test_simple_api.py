"""
Simple integration tests for core FastAPI functionality.

These tests focus on testing the basic FastAPI setup without
complex dependencies like Keycloak.
"""

import pytest
import os
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch


class TestSimpleAPI:
    """Simple integration tests for FastAPI core functionality."""
    
    def test_fastapi_basic_setup(self):
        """Test that FastAPI can be instantiated with basic configuration."""
        app = FastAPI()
        
        @app.get("/test")
        def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        assert response.json() == {"message": "test"}
    
    def test_fastapi_with_environment_variables(self):
        """Test FastAPI with environment variables."""
        app = FastAPI()
        
        @app.get("/env-test")
        def env_test():
            return {
                "host": os.getenv("TEST_HOST", "localhost"),
                "port": int(os.getenv("TEST_PORT", "8000"))
            }
        
        # Test with default values
        client = TestClient(app)
        response = client.get("/env-test")
        
        assert response.status_code == 200
        data = response.json()
        assert data["host"] == "localhost"
        assert data["port"] == 8000
        
        # Test with custom environment variables
        with patch.dict(os.environ, {"TEST_HOST": "0.0.0.0", "TEST_PORT": "9000"}):
            response = client.get("/env-test")
            assert response.status_code == 200
            data = response.json()
            assert data["host"] == "0.0.0.0"
            assert data["port"] == 9000
    
    def test_health_check_pattern(self):
        """Test a simple health check endpoint pattern."""
        app = FastAPI()
        
        @app.get("/health")
        def health_check():
            return {
                "status": "healthy",
                "checks": {
                    "application": {"status": "ok"},
                    "database": {"status": "unknown"}
                }
            }
        
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "checks" in data
        assert data["checks"]["application"]["status"] == "ok"
    
    def test_cors_middleware_pattern(self):
        """Test CORS middleware setup pattern."""
        from fastapi.middleware.cors import CORSMiddleware
        
        app = FastAPI()
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        @app.get("/cors-test")
        def cors_test():
            return {"message": "cors enabled"}
        
        client = TestClient(app)
        response = client.get("/cors-test")
        
        assert response.status_code == 200
        # The TestClient doesn't include CORS headers, but we can verify
        # the middleware is configured by checking the user_middleware list
        user_middleware = app.user_middleware
        middleware_types = [middleware.cls.__name__ for middleware in user_middleware]
        assert 'CORSMiddleware' in middleware_types
    
    def test_static_files_pattern(self):
        """Test static files mounting pattern."""
        from fastapi.staticfiles import StaticFiles
        import tempfile
        
        app = FastAPI()
        
        # Create a temporary directory for static files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test static file
            static_file_path = os.path.join(temp_dir, "test.txt")
            with open(static_file_path, "w") as f:
                f.write("test content")
            
            # Mount static files
            app.mount("/static", StaticFiles(directory=temp_dir), name="static")
            
            client = TestClient(app)
            response = client.get("/static/test.txt")
            
            assert response.status_code == 200
            assert response.text == "test content"
    
    def test_configuration_loading_pattern(self):
        """Test configuration loading pattern used by the app."""
        import yaml
        import tempfile
        from envyaml import EnvYAML
        
        # Create a test configuration
        config_content = {
            'app': {
                'name': '$APP_NAME|test-app',
                'debug': '$APP_DEBUG|false',
                'port': '$APP_PORT|8000'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_content, f)
            config_file = f.name
        
        try:
            # Test configuration loading
            config = EnvYAML(config_file, strict=False)
            
            # Test defaults
            assert config['app']['name'] == 'test-app'
            assert config['app']['debug'] == False
            assert config['app']['port'] == 8000
            
            # Test environment override
            with patch.dict(os.environ, {'APP_NAME': 'prod-app', 'APP_DEBUG': 'true', 'APP_PORT': '9000'}):
                config = EnvYAML(config_file, strict=False)
                assert config['app']['name'] == 'prod-app'
                assert config['app']['debug'] == True
                assert config['app']['port'] == 9000
        
        finally:
            os.unlink(config_file)
    
    def test_pydantic_model_pattern(self):
        """Test Pydantic model pattern used in the app."""
        from pydantic import BaseModel
        from typing import Optional
        
        class AppConfig(BaseModel):
            name: str
            debug: bool = False
            port: int = 8000
            secret: Optional[str] = None
        
        # Test model creation
        config = AppConfig(name="test-app")
        assert config.name == "test-app"
        assert config.debug == False
        assert config.port == 8000
        assert config.secret is None
        
        # Test model validation
        config = AppConfig(name="test-app", debug=True, port=9000)
        assert config.debug == True
        assert config.port == 9000
        
        # Test with FastAPI endpoint
        app = FastAPI()
        
        @app.post("/config")
        def update_config(config: AppConfig):
            return {"received": config.model_dump()}
        
        client = TestClient(app)
        response = client.post("/config", json={
            "name": "api-test",
            "debug": True,
            "port": 8080
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["received"]["name"] == "api-test"
        assert data["received"]["debug"] == True
        assert data["received"]["port"] == 8080