"""
File Streaming Module

Streams files from POSIX filesystem with HTTP Range support.
"""
import os
import logging
from pathlib import Path
from typing import Optional, Tuple
from fastapi import Response
from fastapi.responses import FileResponse, StreamingResponse

logger = logging.getLogger('storage-gateway.streaming.file_stream')


class FileStreamError(Exception):
    """Base exception for file streaming errors."""
    pass


class FileNotFoundError(FileStreamError):
    """Exception raised when file doesn't exist."""
    pass


class PathTraversalError(FileStreamError):
    """Exception raised when path traversal detected."""
    pass


class FileStreamer:
    """
    Streams files from POSIX filesystem.

    Features:
    - Path validation (prevent directory traversal)
    - HTTP Range support (partial content, 206 responses)
    - Chunked streaming for large files
    - Automatic MIME type detection
    """

    CHUNK_SIZE = 1024 * 1024  # 1 MB chunks

    def __init__(self, root_path: str):
        """
        Initialize file streamer.

        :param root_path: Root directory for file access
        """
        self.root_path = Path(root_path).resolve()

        if not self.root_path.exists():
            raise FileStreamError(f"Root path does not exist: {root_path}")

        if not self.root_path.is_dir():
            raise FileStreamError(f"Root path is not a directory: {root_path}")

        logger.info(f"File streamer initialized with root: {self.root_path}")

    def _validate_path(self, relative_path: str) -> Path:
        """
        Validate path and resolve to absolute path.

        Prevents directory traversal attacks (../).

        :param relative_path: Relative path from root
        :return: Validated absolute path
        :raises PathTraversalError: If path traversal detected
        :raises FileNotFoundError: If file doesn't exist
        """
        # Normalize path (remove .., ., etc.)
        normalized = os.path.normpath(relative_path)

        # Check for path traversal
        if normalized.startswith("..") or normalized.startswith("/"):
            logger.error(f"Path traversal attempt: {relative_path}")
            raise PathTraversalError(f"Invalid path: {relative_path}")

        # Resolve to absolute path
        absolute_path = (self.root_path / normalized).resolve()

        # Ensure path is within root
        try:
            absolute_path.relative_to(self.root_path)
        except ValueError:
            logger.error(f"Path outside root: {relative_path} -> {absolute_path}")
            raise PathTraversalError(f"Path outside root: {relative_path}")

        # Check if file exists
        if not absolute_path.exists():
            logger.warning(f"File not found: {relative_path}")
            raise FileNotFoundError(f"File not found: {relative_path}")

        return absolute_path

    def stream_file(
        self,
        path: str,
        range_header: Optional[str] = None
    ) -> Response:
        """
        Stream file with optional HTTP Range support.

        :param path: Relative path from root
        :param range_header: HTTP Range header value (e.g., "bytes=0-1023")
        :return: FastAPI Response (FileResponse or StreamingResponse)
        :raises FileStreamError: If streaming fails
        """
        # Validate path
        absolute_path = self._validate_path(path)

        # Check if it's a file (not directory)
        if not absolute_path.is_file():
            raise FileStreamError(f"Not a file: {path}")

        # Get file size
        file_size = absolute_path.stat().st_size

        # Parse range header if present
        if range_header:
            start, end = self._parse_range(range_header, file_size)
            return self._stream_partial(absolute_path, start, end, file_size)
        else:
            # Stream entire file
            return FileResponse(
                path=str(absolute_path),
                media_type="application/octet-stream",
                filename=absolute_path.name
            )

    def _parse_range(self, range_header: str, file_size: int) -> Tuple[int, int]:
        """
        Parse HTTP Range header.

        :param range_header: Range header value (e.g., "bytes=0-1023")
        :param file_size: Total file size
        :return: (start, end) byte positions
        :raises FileStreamError: If range is invalid
        """
        try:
            # Parse "bytes=start-end"
            if not range_header.startswith("bytes="):
                raise ValueError("Range must start with 'bytes='")

            range_spec = range_header[6:]  # Remove "bytes="

            # Handle different range formats
            if "-" not in range_spec:
                raise ValueError("Invalid range format")

            parts = range_spec.split("-", 1)

            if parts[0] == "":
                # Suffix range: "-500" (last 500 bytes)
                suffix_length = int(parts[1])
                start = max(0, file_size - suffix_length)
                end = file_size - 1
            elif parts[1] == "":
                # Open-ended range: "500-" (from byte 500 to end)
                start = int(parts[0])
                end = file_size - 1
            else:
                # Full range: "0-1023"
                start = int(parts[0])
                end = int(parts[1])

            # Validate range
            if start < 0 or end >= file_size or start > end:
                raise ValueError(f"Invalid range: {start}-{end} (file size: {file_size})")

            return start, end

        except (ValueError, IndexError) as e:
            logger.error(f"Invalid range header: {range_header} - {e}")
            raise FileStreamError(f"Invalid range: {range_header}")

    def _stream_partial(
        self,
        file_path: Path,
        start: int,
        end: int,
        file_size: int
    ) -> StreamingResponse:
        """
        Stream partial file content (HTTP 206 Partial Content).

        :param file_path: Absolute path to file
        :param start: Start byte position
        :param end: End byte position (inclusive)
        :param file_size: Total file size
        :return: StreamingResponse with 206 status
        """
        content_length = end - start + 1

        def iter_chunks():
            """Generator for file chunks."""
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = content_length

                while remaining > 0:
                    chunk_size = min(self.CHUNK_SIZE, remaining)
                    chunk = f.read(chunk_size)

                    if not chunk:
                        break

                    yield chunk
                    remaining -= len(chunk)

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
        }

        logger.info(
            f"Streaming partial file",
            extra={
                "path": str(file_path),
                "range": f"{start}-{end}",
                "size": content_length
            }
        )

        return StreamingResponse(
            iter_chunks(),
            status_code=206,
            headers=headers,
            media_type="application/octet-stream"
        )

    def get_file_info(self, path: str) -> dict:
        """
        Get file metadata.

        :param path: Relative path from root
        :return: Dict with file metadata
        """
        absolute_path = self._validate_path(path)

        stat = absolute_path.stat()

        return {
            "name": absolute_path.name,
            "path": path,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "is_file": absolute_path.is_file(),
            "is_dir": absolute_path.is_dir()
        }
