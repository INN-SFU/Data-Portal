"""
Tests for PosixStorageAgent - Phase 1 Implementation

Tests basic file tree loading, path validation, and placeholder URL generation.
"""
import os
import tempfile
import pytest
from pathlib import Path
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


class TestPosixAgentInitialization:
    """Test agent initialization and configuration."""

    def test_init_with_valid_root(self, temp_storage_root):
        """Test initialization with valid root path."""
        agent = PosixStorageAgent(
            instance_url="http://gateway.local:9000",
            root_path=str(temp_storage_root)
        )

        assert agent.root_path == temp_storage_root
        assert agent.instance_url == "http://gateway.local:9000"
        assert agent.file_tree is not None

    def test_init_with_nonexistent_root(self):
        """Test initialization fails with nonexistent root."""
        with pytest.raises(ValueError, match="Root path does not exist"):
            PosixStorageAgent(
                instance_url="http://gateway.local:9000",
                root_path="/nonexistent/path"
            )

    def test_init_with_file_as_root(self, temp_storage_root):
        """Test initialization fails when root is a file, not directory."""
        file_path = temp_storage_root / "file1.txt"
        with pytest.raises(ValueError, match="Root path is not a directory"):
            PosixStorageAgent(
                instance_url="http://gateway.local:9000",
                root_path=str(file_path)
            )


class TestFileTreeLoading:
    """Test file tree construction."""

    def test_file_tree_contains_all_files(self, temp_storage_root):
        """Test that file tree contains all files."""
        agent = PosixStorageAgent(
            instance_url="http://gateway.local:9000",
            root_path=str(temp_storage_root)
        )

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

    def test_file_tree_uses_forward_slashes(self, temp_storage_root):
        """Test that file tree uses forward slashes regardless of OS."""
        agent = PosixStorageAgent(
            instance_url="http://gateway.local:9000",
            root_path=str(temp_storage_root)
        )

        nested_file_node = agent.file_tree.get_node('subdir2/nested/file5.txt')
        assert nested_file_node is not None
        assert '\\' not in nested_file_node.identifier  # No backslashes


class TestPathValidation:
    """Test path validation and security."""

    def test_validate_safe_path(self, temp_storage_root):
        """Test validation of safe paths."""
        agent = PosixStorageAgent(
            instance_url="http://gateway.local:9000",
            root_path=str(temp_storage_root)
        )

        # Safe paths should validate
        abs_path = agent._validate_path("subdir1/file3.txt")
        assert abs_path == temp_storage_root / "subdir1" / "file3.txt"

    def test_validate_directory_traversal_attack(self, temp_storage_root):
        """Test that directory traversal is blocked."""
        agent = PosixStorageAgent(
            instance_url="http://gateway.local:9000",
            root_path=str(temp_storage_root)
        )

        # Directory traversal should be blocked
        with pytest.raises(ValueError, match="Path outside storage root"):
            agent._validate_path("../../../etc/passwd")

    def test_validate_absolute_path_escape(self, temp_storage_root):
        """Test that absolute paths outside root are blocked."""
        agent = PosixStorageAgent(
            instance_url="http://gateway.local:9000",
            root_path=str(temp_storage_root)
        )

        # Absolute path outside root should be blocked
        with pytest.raises(ValueError, match="Path outside storage root"):
            agent._validate_path("/etc/passwd")


class TestGenerateAccessLink:
    """Test access link generation (Phase 1: placeholder URLs)."""

    def test_write_single_file(self, temp_storage_root):
        """Test write access link for single file."""
        agent = PosixStorageAgent(
            instance_url="http://gateway.local:9000",
            root_path=str(temp_storage_root)
        )

        urls, paths = agent.generate_access_link(
            resource="subdir1/newfile.txt",
            method="write",
            ttl=3600
        )

        assert len(urls) == 1
        assert len(paths) == 1
        assert paths[0] == "subdir1/newfile.txt"
        assert "method=write" in urls[0]
        assert "ttl=3600" in urls[0]

    def test_read_regex_match_multiple(self, temp_storage_root):
        """Test read access links with regex matching multiple files."""
        agent = PosixStorageAgent(
            instance_url="http://gateway.local:9000",
            root_path=str(temp_storage_root)
        )

        # Match all .txt files
        urls, paths = agent.generate_access_link(
            resource=r".*\.txt",
            method="read",
            ttl=3600
        )

        # Should match: file1.txt, subdir1/file3.txt, subdir2/nested/file5.txt
        assert len(paths) == 3
        assert len(urls) == 3

        txt_files = ['file1.txt', 'subdir1/file3.txt', 'subdir2/nested/file5.txt']
        for txt_file in txt_files:
            assert txt_file in paths

    def test_read_regex_match_single(self, temp_storage_root):
        """Test read access link with regex matching single file."""
        agent = PosixStorageAgent(
            instance_url="http://gateway.local:9000",
            root_path=str(temp_storage_root)
        )

        # Exact match for one file
        urls, paths = agent.generate_access_link(
            resource=r"file1\.txt",
            method="read",
            ttl=1800
        )

        assert len(paths) == 1
        assert paths[0] == "file1.txt"
        assert "method=read" in urls[0]
        assert "ttl=1800" in urls[0]

    def test_read_no_matches(self, temp_storage_root):
        """Test read access link with no matches."""
        agent = PosixStorageAgent(
            instance_url="http://gateway.local:9000",
            root_path=str(temp_storage_root)
        )

        # No matches
        urls, paths = agent.generate_access_link(
            resource=r"nonexistent.*",
            method="read",
            ttl=3600
        )

        assert len(urls) == 0
        assert len(paths) == 0

    def test_unsupported_method(self, temp_storage_root):
        """Test that unsupported methods are rejected."""
        agent = PosixStorageAgent(
            instance_url="http://gateway.local:9000",
            root_path=str(temp_storage_root)
        )

        with pytest.raises(ValueError, match="Unsupported method"):
            agent.generate_access_link(
                resource="file1.txt",
                method="delete",
                ttl=3600
            )

    def test_invalid_regex(self, temp_storage_root):
        """Test that invalid regex patterns are rejected."""
        agent = PosixStorageAgent(
            instance_url="http://gateway.local:9000",
            root_path=str(temp_storage_root)
        )

        with pytest.raises(ValueError, match="Invalid regex pattern"):
            agent.generate_access_link(
                resource="[invalid(regex",
                method="read",
                ttl=3600
            )


class TestAgentMethods:
    """Test other agent methods."""

    def test_config(self, temp_storage_root):
        """Test config method."""
        agent = PosixStorageAgent(
            instance_url="http://gateway.local:9000",
            root_path=str(temp_storage_root)
        )

        config = agent.config(secrets=False)
        assert config['instance_url'] == "http://gateway.local:9000"
        assert config['root_path'] == str(temp_storage_root)

    def test_secrets(self, temp_storage_root):
        """Test that secrets are empty in Phase 1."""
        agent = PosixStorageAgent(
            instance_url="http://gateway.local:9000",
            root_path=str(temp_storage_root)
        )

        secrets = agent._secrets()
        assert secrets == {}

    def test_refresh_connection(self, temp_storage_root):
        """Test connection refresh reloads file tree."""
        agent = PosixStorageAgent(
            instance_url="http://gateway.local:9000",
            root_path=str(temp_storage_root)
        )

        original_count = len(agent.file_tree.all_nodes())

        # Add a new file
        (temp_storage_root / "newfile.txt").write_text("new content")

        # Refresh should reload tree
        agent.refresh_connection()
        new_count = len(agent.file_tree.all_nodes())

        assert new_count == original_count + 1
        assert agent.file_tree.get_node('newfile.txt') is not None

    def test_close(self, temp_storage_root):
        """Test close method (should not raise)."""
        agent = PosixStorageAgent(
            instance_url="http://gateway.local:9000",
            root_path=str(temp_storage_root)
        )

        # Should not raise
        agent.close()

    def test_str_representation(self, temp_storage_root):
        """Test string representation."""
        agent = PosixStorageAgent(
            instance_url="http://gateway.local:9000",
            root_path=str(temp_storage_root)
        )

        str_repr = str(agent)
        assert "PosixStorageAgent" in str_repr
        assert str(temp_storage_root) in str_repr
        assert "http://gateway.local:9000" in str_repr
