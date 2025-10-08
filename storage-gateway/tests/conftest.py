"""
Pytest configuration and fixtures for storage-gateway tests.
"""
import pytest


@pytest.fixture(scope="session")
def httpserver_listen_address():
    """Configure pytest-httpserver to listen on localhost."""
    return ("127.0.0.1", 0)
