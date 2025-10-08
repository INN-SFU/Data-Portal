"""
Tests for File Streaming

Tests file streaming with path validation and HTTP Range support.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from streaming.file_stream import FileStreamer, FileNotFoundError, PathTraversalError


class TestFileStreamer:
    """Test file streamer functionality."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory with test files."""
        temp_dir = tempfile.mkdtemp()

        # Create test files
        (Path(temp_dir) / "file1.txt").write_text("Hello World")
        (Path(temp_dir) / "folder1").mkdir()
        (Path(temp_dir) / "folder1" / "file2.txt").write_text("Nested file")

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_init_with_valid_path(self, temp_storage):
        """Test initialization with valid root path."""
        streamer = FileStreamer(root_path=temp_storage)
        assert streamer.root_path == Path(temp_storage).resolve()

    def test_init_with_invalid_path(self):
        """Test initialization with invalid root path."""
        with pytest.raises(Exception, match="does not exist"):
            FileStreamer(root_path="/nonexistent/path")

    def test_validate_path_success(self, temp_storage):
        """Test path validation with valid path."""
        streamer = FileStreamer(root_path=temp_storage)
        validated = streamer._validate_path("file1.txt")
        assert validated.exists()
        assert validated.name == "file1.txt"

    def test_validate_path_traversal_fails(self, temp_storage):
        """Test that path traversal is rejected."""
        streamer = FileStreamer(root_path=temp_storage)

        with pytest.raises(PathTraversalError):
            streamer._validate_path("../etc/passwd")

        with pytest.raises(PathTraversalError):
            streamer._validate_path("/etc/passwd")

    def test_validate_path_not_found(self, temp_storage):
        """Test that missing files are rejected."""
        streamer = FileStreamer(root_path=temp_storage)

        with pytest.raises(FileNotFoundError):
            streamer._validate_path("nonexistent.txt")

    def test_stream_file_success(self, temp_storage):
        """Test streaming a file."""
        streamer = FileStreamer(root_path=temp_storage)
        response = streamer.stream_file("file1.txt")

        assert response is not None
        # FileResponse is returned for full file

    def test_parse_range_full(self, temp_storage):
        """Test parsing full range (0-1023)."""
        streamer = FileStreamer(root_path=temp_storage)
        start, end = streamer._parse_range("bytes=0-1023", file_size=2048)

        assert start == 0
        assert end == 1023

    def test_parse_range_suffix(self, temp_storage):
        """Test parsing suffix range (-500)."""
        streamer = FileStreamer(root_path=temp_storage)
        start, end = streamer._parse_range("bytes=-500", file_size=1000)

        assert start == 500
        assert end == 999

    def test_parse_range_open_ended(self, temp_storage):
        """Test parsing open-ended range (500-)."""
        streamer = FileStreamer(root_path=temp_storage)
        start, end = streamer._parse_range("bytes=500-", file_size=1000)

        assert start == 500
        assert end == 999

    def test_get_file_info(self, temp_storage):
        """Test getting file metadata."""
        streamer = FileStreamer(root_path=temp_storage)
        info = streamer.get_file_info("file1.txt")

        assert info["name"] == "file1.txt"
        assert info["path"] == "file1.txt"
        assert info["size"] == 11  # "Hello World"
        assert info["is_file"] is True
        assert info["is_dir"] is False
