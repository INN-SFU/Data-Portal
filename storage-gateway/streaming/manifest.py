"""
Manifest Generation Module

Generates JSON manifests listing files in folders.
"""
import os
import logging
from pathlib import Path
from typing import List, Dict, Any
from fastapi.responses import JSONResponse

logger = logging.getLogger('storage-gateway.streaming.manifest')


class ManifestError(Exception):
    """Base exception for manifest errors."""
    pass


class ManifestGenerator:
    """
    Generates JSON manifests for folders.

    Features:
    - Recursive directory listing
    - File metadata (size, modified time)
    - Path validation
    - JSON response format
    """

    def __init__(self, root_path: str):
        """
        Initialize manifest generator.

        :param root_path: Root directory for file access
        """
        self.root_path = Path(root_path).resolve()

        if not self.root_path.exists():
            raise ManifestError(f"Root path does not exist: {root_path}")

        if not self.root_path.is_dir():
            raise ManifestError(f"Root path is not a directory: {root_path}")

        logger.info(f"Manifest generator initialized with root: {self.root_path}")

    def _validate_path(self, relative_path: str) -> Path:
        """
        Validate path and resolve to absolute path.

        :param relative_path: Relative path from root
        :return: Validated absolute path
        :raises ManifestError: If path invalid or outside root
        """
        # Normalize path
        normalized = os.path.normpath(relative_path)

        # Check for path traversal
        if normalized.startswith("..") or normalized.startswith("/"):
            logger.error(f"Path traversal attempt: {relative_path}")
            raise ManifestError(f"Invalid path: {relative_path}")

        # Resolve to absolute path
        absolute_path = (self.root_path / normalized).resolve()

        # Ensure path is within root
        try:
            absolute_path.relative_to(self.root_path)
        except ValueError:
            logger.error(f"Path outside root: {relative_path} -> {absolute_path}")
            raise ManifestError(f"Path outside root: {relative_path}")

        # Check if path exists
        if not absolute_path.exists():
            logger.warning(f"Path not found: {relative_path}")
            raise ManifestError(f"Path not found: {relative_path}")

        return absolute_path

    def generate_manifest(
        self,
        path: str,
        recursive: bool = False,
        include_hidden: bool = False
    ) -> JSONResponse:
        """
        Generate JSON manifest for folder.

        :param path: Relative path from root
        :param recursive: Include subdirectories recursively
        :param include_hidden: Include hidden files (starting with .)
        :return: JSONResponse with file listing
        :raises ManifestError: If path is not a directory
        """
        # Validate path
        absolute_path = self._validate_path(path)

        # Check if it's a directory
        if not absolute_path.is_dir():
            raise ManifestError(f"Not a directory: {path}")

        # Generate file listing
        if recursive:
            files = self._list_recursive(absolute_path, include_hidden)
        else:
            files = self._list_directory(absolute_path, include_hidden)

        # Build manifest
        manifest = {
            "path": path,
            "type": "directory",
            "file_count": len(files),
            "files": files
        }

        logger.info(
            f"Generated manifest",
            extra={
                "path": path,
                "file_count": len(files),
                "recursive": recursive
            }
        )

        return JSONResponse(content=manifest)

    def _list_directory(self, dir_path: Path, include_hidden: bool) -> List[Dict[str, Any]]:
        """
        List files in a single directory (non-recursive).

        :param dir_path: Absolute path to directory
        :param include_hidden: Include hidden files
        :return: List of file metadata dicts
        """
        files = []

        try:
            for entry in sorted(dir_path.iterdir(), key=lambda p: (not p.is_file(), p.name)):
                # Skip hidden files if requested
                if not include_hidden and entry.name.startswith("."):
                    continue

                # Get relative path from root
                relative_path = str(entry.relative_to(self.root_path))

                # Get file metadata
                stat = entry.stat()

                file_info = {
                    "name": entry.name,
                    "path": relative_path,
                    "type": "file" if entry.is_file() else "directory",
                    "size": stat.st_size if entry.is_file() else None,
                    "modified": stat.st_mtime
                }

                files.append(file_info)

        except PermissionError as e:
            logger.error(f"Permission denied accessing directory: {dir_path}")
            raise ManifestError(f"Permission denied: {e}")

        return files

    def _list_recursive(self, dir_path: Path, include_hidden: bool) -> List[Dict[str, Any]]:
        """
        List files recursively in directory tree.

        :param dir_path: Absolute path to directory
        :param include_hidden: Include hidden files
        :return: List of file metadata dicts
        """
        files = []

        try:
            for root, dirs, filenames in os.walk(dir_path):
                root_path = Path(root)

                # Filter hidden directories
                if not include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith(".")]

                # Add files
                for filename in sorted(filenames):
                    # Skip hidden files if requested
                    if not include_hidden and filename.startswith("."):
                        continue

                    file_path = root_path / filename
                    relative_path = str(file_path.relative_to(self.root_path))

                    try:
                        stat = file_path.stat()

                        file_info = {
                            "name": filename,
                            "path": relative_path,
                            "type": "file",
                            "size": stat.st_size,
                            "modified": stat.st_mtime
                        }

                        files.append(file_info)

                    except (OSError, PermissionError) as e:
                        logger.warning(f"Skipping file due to error: {file_path} - {e}")

        except PermissionError as e:
            logger.error(f"Permission denied during recursive walk: {dir_path}")
            raise ManifestError(f"Permission denied: {e}")

        return files

    def get_directory_info(self, path: str) -> dict:
        """
        Get directory metadata (without listing files).

        :param path: Relative path from root
        :return: Dict with directory metadata
        """
        absolute_path = self._validate_path(path)

        if not absolute_path.is_dir():
            raise ManifestError(f"Not a directory: {path}")

        stat = absolute_path.stat()

        # Count immediate children
        try:
            children = list(absolute_path.iterdir())
            file_count = sum(1 for c in children if c.is_file())
            dir_count = sum(1 for c in children if c.is_dir())
        except PermissionError:
            file_count = None
            dir_count = None

        return {
            "name": absolute_path.name,
            "path": path,
            "type": "directory",
            "modified": stat.st_mtime,
            "file_count": file_count,
            "dir_count": dir_count
        }
