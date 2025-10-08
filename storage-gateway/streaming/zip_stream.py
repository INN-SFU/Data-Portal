"""
ZIP Streaming Module

On-the-fly ZIP compression for folder downloads.
Streams ZIP archive without loading entire folder in memory.
"""
import os
import logging
from pathlib import Path
from typing import Optional, Iterator
from zipfile import ZipFile, ZIP_DEFLATED
from io import BytesIO
from fastapi.responses import StreamingResponse

logger = logging.getLogger('storage-gateway.streaming.zip_stream')


class ZipStreamError(Exception):
    """Base exception for ZIP streaming errors."""
    pass


class ZipStreamer:
    """
    Streams ZIP archives on-the-fly from POSIX filesystem.

    Features:
    - On-the-fly compression (doesn't load entire folder in memory)
    - Recursive directory traversal
    - Path validation (prevent directory traversal)
    - Streaming response for large folders
    """

    CHUNK_SIZE = 64 * 1024  # 64 KB chunks

    def __init__(self, root_path: str):
        """
        Initialize ZIP streamer.

        :param root_path: Root directory for file access
        """
        self.root_path = Path(root_path).resolve()

        if not self.root_path.exists():
            raise ZipStreamError(f"Root path does not exist: {root_path}")

        if not self.root_path.is_dir():
            raise ZipStreamError(f"Root path is not a directory: {root_path}")

        logger.info(f"ZIP streamer initialized with root: {self.root_path}")

    def _validate_path(self, relative_path: str) -> Path:
        """
        Validate path and resolve to absolute path.

        :param relative_path: Relative path from root
        :return: Validated absolute path
        :raises ZipStreamError: If path invalid or outside root
        """
        # Normalize path
        normalized = os.path.normpath(relative_path)

        # Check for path traversal
        if normalized.startswith("..") or normalized.startswith("/"):
            logger.error(f"Path traversal attempt: {relative_path}")
            raise ZipStreamError(f"Invalid path: {relative_path}")

        # Resolve to absolute path
        absolute_path = (self.root_path / normalized).resolve()

        # Ensure path is within root
        try:
            absolute_path.relative_to(self.root_path)
        except ValueError:
            logger.error(f"Path outside root: {relative_path} -> {absolute_path}")
            raise ZipStreamError(f"Path outside root: {relative_path}")

        # Check if path exists
        if not absolute_path.exists():
            logger.warning(f"Path not found: {relative_path}")
            raise ZipStreamError(f"Path not found: {relative_path}")

        return absolute_path

    def stream_zip(
        self,
        path: str,
        include_hidden: bool = False,
        compression_level: int = 6
    ) -> StreamingResponse:
        """
        Stream folder as ZIP archive.

        :param path: Relative path from root (must be directory)
        :param include_hidden: Include hidden files (starting with .)
        :param compression_level: ZIP compression level (0-9, default: 6)
        :return: StreamingResponse with ZIP content
        :raises ZipStreamError: If path is not a directory
        """
        # Validate path
        absolute_path = self._validate_path(path)

        # Check if it's a directory
        if not absolute_path.is_dir():
            # Allow single file to be zipped
            if absolute_path.is_file():
                return self._stream_single_file_zip(absolute_path, compression_level)
            else:
                raise ZipStreamError(f"Not a file or directory: {path}")

        # Determine ZIP filename
        zip_filename = f"{absolute_path.name or 'download'}.zip"

        logger.info(
            f"Streaming ZIP archive",
            extra={
                "path": path,
                "include_hidden": include_hidden,
                "compression_level": compression_level
            }
        )

        # Stream ZIP
        return StreamingResponse(
            self._generate_zip(absolute_path, include_hidden, compression_level),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{zip_filename}"'
            }
        )

    def _generate_zip(
        self,
        dir_path: Path,
        include_hidden: bool,
        compression_level: int
    ) -> Iterator[bytes]:
        """
        Generator that yields ZIP chunks on-the-fly.

        Uses BytesIO buffer to accumulate ZIP data and yields chunks.

        :param dir_path: Absolute path to directory
        :param include_hidden: Include hidden files
        :param compression_level: ZIP compression level (0-9)
        :yield: ZIP data chunks
        """
        # Create in-memory buffer for ZIP
        buffer = BytesIO()

        try:
            # Create ZIP file in buffer
            with ZipFile(buffer, 'w', ZIP_DEFLATED, compresslevel=compression_level) as zipf:
                # Walk directory tree
                for root, dirs, files in os.walk(dir_path):
                    root_path = Path(root)

                    # Filter hidden directories
                    if not include_hidden:
                        dirs[:] = [d for d in dirs if not d.startswith(".")]

                    # Add files to ZIP
                    for filename in sorted(files):
                        # Skip hidden files if requested
                        if not include_hidden and filename.startswith("."):
                            continue

                        file_path = root_path / filename

                        # Get relative path from target directory (for ZIP archive structure)
                        try:
                            arcname = str(file_path.relative_to(dir_path))
                        except ValueError:
                            logger.warning(f"Skipping file outside target: {file_path}")
                            continue

                        # Add file to ZIP
                        try:
                            zipf.write(file_path, arcname=arcname)
                            logger.debug(f"Added to ZIP: {arcname}")

                            # Yield chunks if buffer is getting large
                            if buffer.tell() > self.CHUNK_SIZE:
                                buffer.seek(0)
                                chunk = buffer.read()
                                if chunk:
                                    yield chunk
                                buffer.seek(0)
                                buffer.truncate(0)

                        except (OSError, PermissionError) as e:
                            logger.warning(f"Failed to add file to ZIP: {file_path} - {e}")

            # Yield any remaining data
            buffer.seek(0)
            remaining = buffer.read()
            if remaining:
                yield remaining

        except Exception as e:
            logger.error(f"Error generating ZIP: {e}")
            raise ZipStreamError(f"Failed to generate ZIP: {e}")

        finally:
            buffer.close()

    def _stream_single_file_zip(
        self,
        file_path: Path,
        compression_level: int
    ) -> StreamingResponse:
        """
        Stream a single file as ZIP archive.

        :param file_path: Absolute path to file
        :param compression_level: ZIP compression level
        :return: StreamingResponse with ZIP content
        """
        zip_filename = f"{file_path.stem}.zip"

        def generate():
            buffer = BytesIO()
            try:
                with ZipFile(buffer, 'w', ZIP_DEFLATED, compresslevel=compression_level) as zipf:
                    zipf.write(file_path, arcname=file_path.name)

                buffer.seek(0)
                yield buffer.read()
            finally:
                buffer.close()

        logger.info(f"Streaming single file as ZIP: {file_path}")

        return StreamingResponse(
            generate(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{zip_filename}"'
            }
        )

    def estimate_zip_size(self, path: str, include_hidden: bool = False) -> dict:
        """
        Estimate ZIP archive size (for debugging/monitoring).

        :param path: Relative path from root
        :param include_hidden: Include hidden files
        :return: Dict with size estimates
        """
        absolute_path = self._validate_path(path)

        if not absolute_path.is_dir():
            raise ZipStreamError(f"Not a directory: {path}")

        total_size = 0
        file_count = 0

        try:
            for root, dirs, files in os.walk(absolute_path):
                root_path = Path(root)

                if not include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith(".")]

                for filename in files:
                    if not include_hidden and filename.startswith("."):
                        continue

                    file_path = root_path / filename

                    try:
                        total_size += file_path.stat().st_size
                        file_count += 1
                    except (OSError, PermissionError):
                        pass

        except PermissionError as e:
            logger.error(f"Permission denied estimating size: {absolute_path}")
            raise ZipStreamError(f"Permission denied: {e}")

        # Rough estimate: ZIP is typically 60-90% of original size (depends on compression)
        estimated_zip_size = int(total_size * 0.75)

        return {
            "file_count": file_count,
            "uncompressed_size": total_size,
            "estimated_zip_size": estimated_zip_size
        }
