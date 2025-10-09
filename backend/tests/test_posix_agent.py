"""
Tests for PosixStorageAgent - Phase 4 Implementation

Tests file tree loading, path validation, and JWT token generation via Storage Issuer.
"""
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from core.connectivity.agents.posix_agent import PosixStorageAgent


@pytest.fixture
def temp_storage_root():
    """Create a temporary directory structure for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create test directory structure:
        # /
        # ├── file1.txt
        # ├── file2.dat
        # ├── subdir1/
        # │   ├── file3.txt
        # │   └── file4.dat
        # └── subdir2/
        #     └── nested/
        #         └── file5.txt

        (root / "file1.txt").write_text("content1")
        (root / "file2.dat").write_text("content2")

        (root / "subdir1").mkdir()
        (root / "subdir1" / "file3.txt").write_text("content3")
        (root / "subdir1" / "file4.dat").write_text("content4")

        (root / "subdir2" / "nested").mkdir(parents=True)
        (root / "subdir2" / "nested" / "file5.txt").write_text("content5")

        yield root


@pytest.fixture
def agent_config():
    """Standard configuration for test agents."""
    return {
        'instance_url': 'http://gateway.local:9000',
        'issuer_url': 'http://issuer.local:8001',
        'issuer_api_key': 'test-api-key',
        'instance_uuid': 'test-instance-uuid'
        # Note: root_path is no longer a user-provided config
    }


@pytest.fixture
def mock_gateway_tree():
    """Mock Gateway /api/tree endpoint with standard test files."""
    with patch('core.connectivity.agents.posix_agent.requests.get') as mock_get:
        mock_get.return_value.json.return_value = {
            'files': [
                'file1.txt',
                'file2.dat',
                'subdir1',
                'subdir1/file3.txt',
                'subdir1/file4.dat',
                'subdir2',
                'subdir2/nested',
                'subdir2/nested/file5.txt'
            ]
        }
        mock_get.return_value.raise_for_status = Mock()
        yield mock_get


class TestPosixAgentInitialization:
    """Test agent initialization and configuration."""

    @patch('core.connectivity.agents.posix_agent.requests.get')
    def test_init_with_valid_gateway(self, mock_get, temp_storage_root, agent_config):
        """Test initialization with valid Gateway connection."""
        # Mock Gateway /api/tree endpoint
        mock_get.return_value.json.return_value = {
            'files': ['file1.txt', 'file2.dat', 'subdir1/file3.txt']
        }
        mock_get.return_value.raise_for_status = Mock()

        agent = PosixStorageAgent(**agent_config)

        assert agent.instance_url == agent_config['instance_url']
        assert agent.issuer_url == agent_config['issuer_url']
        assert agent.instance_uuid == agent_config['instance_uuid']
        assert agent.file_tree is not None

        # Verify Gateway was called
        mock_get.assert_called_once()
        assert '/api/tree' in mock_get.call_args[0][0]

    @patch('core.connectivity.agents.posix_agent.requests.get')
    def test_init_gateway_connection_failure(self, mock_get, agent_config):
        """Test initialization fails if Gateway unreachable."""
        import requests
        mock_get.side_effect = requests.RequestException("Connection refused")

        with pytest.raises(ValueError, match="Failed to load file tree from Gateway"):
            PosixStorageAgent(**agent_config)


class TestFileTreeLoading:
    """Test file tree construction."""

    def test_file_tree_contains_all_files(self, mock_gateway_tree, agent_config):
        """Test that file tree contains all files."""
        agent = PosixStorageAgent(**agent_config)

        # Get all identifiers (excluding root)
        all_ids = [n.identifier for n in agent.file_tree.all_nodes() if n.identifier != 'root']

        # Should contain all files and directories
        expected = [
            'file1.txt',
            'file2.dat',
            'subdir1',
            'subdir1/file3.txt',
            'subdir1/file4.dat',
            'subdir2',
            'subdir2/nested',
            'subdir2/nested/file5.txt'
        ]

        for item in expected:
            assert item in all_ids, f"Missing {item} in file tree"

    def test_file_tree_uses_forward_slashes(self, mock_gateway_tree, agent_config):
        """Test that file tree uses forward slashes regardless of OS."""
        agent = PosixStorageAgent(**agent_config)

        nested_file_node = agent.file_tree.get_node('subdir2/nested/file5.txt')
        assert nested_file_node is not None
        assert '\\' not in nested_file_node.identifier  # No backslashes


class TestPathValidation:
    """Test path validation and security."""

    def test_validate_safe_path(self, mock_gateway_tree, agent_config):
        """Test validation of safe paths."""
        agent = PosixStorageAgent(**agent_config)

        # Safe paths should not raise
        agent._validate_path("subdir1/file3.txt")  # Should not raise

    def test_validate_directory_traversal_attack(self, mock_gateway_tree, agent_config):
        """Test that directory traversal is blocked."""
        agent = PosixStorageAgent(**agent_config)

        # Directory traversal should be blocked
        with pytest.raises(ValueError, match="Invalid path"):
            agent._validate_path("../../../etc/passwd")

    def test_validate_absolute_path_escape(self, mock_gateway_tree, agent_config):
        """Test that absolute paths are blocked."""
        agent = PosixStorageAgent(**agent_config)

        # Absolute path should be blocked
        with pytest.raises(ValueError, match="Invalid path"):
            agent._validate_path("/etc/passwd")


class TestGenerateAccessLink:
    """Test access link generation with JWT tokens via Storage Issuer."""

    @patch('core.connectivity.agents.posix_agent.requests.post')
    def test_write_single_file(self, mock_post, mock_gateway_tree, agent_config):
        """Test write access link for single file."""
        # Mock Issuer response
        mock_post.return_value.json.return_value = {
            'token': 'eyJhbGc...',
            'download_url': 'http://gateway.local:9000/download?token=eyJhbGc...',
            'expires_at': '2025-10-09T15:00:00Z'
        }
        mock_post.return_value.raise_for_status = Mock()

        agent = PosixStorageAgent(**agent_config)

        urls, paths = agent.generate_access_link(
            resource="subdir1/newfile.txt",
            method="write",
            ttl=3600,
            user_uuid="test-user"
        )

        assert len(urls) == 1
        assert len(paths) == 1
        assert paths[0] == "subdir1/newfile.txt"
        assert "token=" in urls[0]
        assert "download" in urls[0]

        # Verify Issuer was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]['json']['path'] == "subdir1/newfile.txt"
        assert call_args[1]['json']['op'] == "write"
        assert call_args[1]['json']['ttl'] == 3600
        assert call_args[1]['json']['user_uuid'] == "test-user"

    @patch('core.connectivity.agents.posix_agent.requests.post')
    def test_read_regex_match_multiple(self, mock_post, mock_gateway_tree, agent_config):
        """Test read access links with regex matching multiple files."""
        # Mock Issuer to return different tokens for each file
        def mock_response(*args, **kwargs):
            path = kwargs['json']['path']
            response = Mock()
            response.json.return_value = {
                'token': f'token-for-{path}',
                'download_url': f'http://gateway.local:9000/download?token=token-for-{path}',
                'expires_at': '2025-10-09T15:00:00Z'
            }
            response.raise_for_status = Mock()
            return response

        mock_post.side_effect = mock_response

        agent = PosixStorageAgent(**agent_config)

        # Match all .txt files
        urls, paths = agent.generate_access_link(
            resource=r".*\.txt",
            method="read",
            ttl=3600,
            user_uuid="test-user"
        )

        # Should match: file1.txt, subdir1/file3.txt, subdir2/nested/file5.txt
        assert len(paths) == 3
        assert len(urls) == 3

        txt_files = ['file1.txt', 'subdir1/file3.txt', 'subdir2/nested/file5.txt']
        for txt_file in txt_files:
            assert txt_file in paths

        # Verify Issuer was called 3 times
        assert mock_post.call_count == 3

    @patch('core.connectivity.agents.posix_agent.requests.post')
    def test_read_regex_match_single(self, mock_post, mock_gateway_tree, agent_config):
        """Test read access link with regex matching single file."""
        mock_post.return_value.json.return_value = {
            'token': 'eyJhbGc...',
            'download_url': 'http://gateway.local:9000/download?token=eyJhbGc...',
            'expires_at': '2025-10-09T15:00:00Z'
        }
        mock_post.return_value.raise_for_status = Mock()

        agent = PosixStorageAgent(**agent_config)

        # Exact match for one file
        urls, paths = agent.generate_access_link(
            resource=r"file1\.txt",
            method="read",
            ttl=1800,
            user_uuid="test-user"
        )

        assert len(paths) == 1
        assert paths[0] == "file1.txt"
        assert "token=" in urls[0]

    def test_read_no_matches(self, mock_gateway_tree, agent_config):
        """Test read access link with no matches."""
        agent = PosixStorageAgent(**agent_config)

        # No matches - should not call Issuer
        urls, paths = agent.generate_access_link(
            resource=r"nonexistent.*",
            method="read",
            ttl=3600,
            user_uuid="test-user"
        )

        assert len(urls) == 0
        assert len(paths) == 0

    def test_unsupported_method(self, mock_gateway_tree, agent_config):
        """Test that unsupported methods are rejected."""
        agent = PosixStorageAgent(**agent_config)

        with pytest.raises(ValueError, match="Unsupported method"):
            agent.generate_access_link(
                resource="file1.txt",
                method="delete",
                ttl=3600,
                user_uuid="test-user"
            )

    def test_invalid_regex(self, mock_gateway_tree, agent_config):
        """Test that invalid regex patterns are rejected."""
        agent = PosixStorageAgent(**agent_config)

        with pytest.raises(ValueError, match="Invalid regex pattern"):
            agent.generate_access_link(
                resource="[invalid(regex",
                method="read",
                ttl=3600,
                user_uuid="test-user"
            )


class TestAgentMethods:
    """Test other agent methods."""

    def test_config(self, mock_gateway_tree, agent_config):
        """Test config method."""
        agent = PosixStorageAgent(**agent_config)

        config = agent.config(secrets=False)
        assert config['instance_url'] == agent_config['instance_url']
        assert config['instance_uuid'] == agent_config['instance_uuid']
        # issuer_url and issuer_api_key are internal backend config, not exposed
        assert 'issuer_url' not in config
        assert 'issuer_api_key' not in config
        assert 'root_path' not in config  # Not exposed in config

    def test_config_with_secrets(self, mock_gateway_tree, agent_config):
        """Test config method with secrets enabled."""
        agent = PosixStorageAgent(**agent_config)

        config = agent.config(secrets=True)
        assert config['issuer_api_key'] == agent_config['issuer_api_key']

    def test_secrets(self, mock_gateway_tree, agent_config):
        """Test that secrets contains issuer_api_key."""
        agent = PosixStorageAgent(**agent_config)

        secrets = agent._secrets()
        assert 'issuer_api_key' in secrets
        assert secrets['issuer_api_key'] == agent_config['issuer_api_key']

    @patch('core.connectivity.agents.posix_agent.requests.get')
    def test_refresh_connection(self, mock_get, mock_gateway_tree, agent_config):
        """Test connection refresh reloads file tree from Gateway."""
        agent = PosixStorageAgent(**agent_config)

        original_count = len(agent.file_tree.all_nodes())

        # Mock Gateway returning updated tree with new file
        mock_get.return_value.json.return_value = {
            'files': ['file1.txt', 'file2.dat', 'newfile.txt']
        }
        mock_get.return_value.raise_for_status = Mock()

        # Refresh should reload tree from Gateway
        agent.refresh_connection()
        new_count = len(agent.file_tree.all_nodes())

        assert new_count == 4  # root + 3 files
        assert agent.file_tree.get_node('newfile.txt') is not None

    def test_close(self, mock_gateway_tree, agent_config):
        """Test close method (should not raise)."""
        agent = PosixStorageAgent(**agent_config)

        # Should not raise
        agent.close()

    def test_str_representation(self, mock_gateway_tree, agent_config):
        """Test string representation."""
        agent = PosixStorageAgent(**agent_config)

        str_repr = str(agent)
        assert "PosixStorageAgent" in str_repr
        assert agent_config['instance_url'] in str_repr
        # issuer_url is internal config, not shown in string representation
