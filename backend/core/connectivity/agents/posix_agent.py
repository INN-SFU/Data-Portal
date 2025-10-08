import os
import re
import logging
import treelib
from typing import List, Tuple
from pathlib import Path
from core.connectivity import AbstractStorageAgent

logger = logging.getLogger('storage.posix')


class PosixStorageAgent(AbstractStorageAgent):
    """
    POSIX Storage Agent for local filesystem access.

    Phase 1 Implementation: Basic file tree and path handling.
    Future phases will add presigned URL support via JWT tokens.

    Attributes:
        FLAVOUR: Storage agent type identifier
        CONFIG: Required configuration parameters
        root_path: Absolute path to storage root directory
    """

    FLAVOUR: str = 'posix'
    CONFIG: dict = {
        "root_path": str  # Absolute path to storage root
    }

    def __init__(self, instance_url: str, root_path: str):
        """
        Initialize POSIX storage agent.

        :param instance_url: Base URL for file access (future: gateway service URL)
        :param root_path: Absolute path to the storage root directory
        :raises ValueError: If root_path doesn't exist or isn't a directory
        """
        super().__init__(instance_url)

        # Validate and normalize root path
        self.root_path = Path(root_path).resolve()
        if not self.root_path.exists():
            raise ValueError(f"Root path does not exist: {root_path}")
        if not self.root_path.is_dir():
            raise ValueError(f"Root path is not a directory: {root_path}")

        logger.info(f"Initializing POSIX agent with root: {self.root_path}")

        # Build the in-memory file tree
        self.file_tree = treelib.Tree()
        self._load_file_tree()

    def _load_file_tree(self):
        """
        Load the file tree by walking the POSIX filesystem.
        Creates nodes for all files and directories under root_path.
        Paths in the tree are relative to root_path.
        """
        # Clear existing tree and recreate root
        self.file_tree = treelib.Tree()
        self.file_tree.create_node('root', 'root')

        try:
            # Walk the filesystem starting from root_path
            for root_dir, dirs, files in os.walk(self.root_path):
                # Get path relative to storage root
                rel_root = Path(root_dir).relative_to(self.root_path)

                # Add all files in this directory
                for file_name in files:
                    if rel_root == Path('.'):
                        # Files directly in root
                        path = file_name
                    else:
                        # Files in subdirectories - use forward slash separator
                        rel_path = str(rel_root).replace(os.path.sep, self.separator)
                        path = f"{rel_path}{self.separator}{file_name}"

                    self._add_file_to_tree(path)

                # Add directories (even if empty) to the tree
                for dir_name in dirs:
                    if rel_root == Path('.'):
                        path = dir_name
                    else:
                        rel_path = str(rel_root).replace(os.path.sep, self.separator)
                        path = f"{rel_path}{self.separator}{dir_name}"

                    self._add_file_to_tree(path)

            logger.info(f"Loaded {len(self.file_tree.all_nodes()) - 1} items into file tree")

        except Exception as e:
            logger.error(f"Error loading file tree: {e}")
            raise

    def _validate_path(self, resource: str) -> Path:
        """
        Validate that a resource path is safe and within the storage root.
        Prevents directory traversal attacks.

        :param resource: Relative path to validate
        :return: Absolute resolved path
        :raises ValueError: If path is invalid or outside root
        """
        # Construct absolute path
        abs_path = (self.root_path / resource).resolve()

        # Ensure it's within the root (prevents directory traversal)
        try:
            abs_path.relative_to(self.root_path)
        except ValueError:
            raise ValueError(f"Path outside storage root: {resource}")

        return abs_path

    def generate_access_link(
        self, resource: str, method: str, ttl: int
    ) -> Tuple[List[str], List[str]]:
        """
        Generate access links for POSIX resources.

        Phase 1: Returns placeholder URLs and matched paths.
        Future phases will call the Issuer service to generate JWT presigned URLs.

        :param resource: Resource path or regex pattern
        :param method: Access method ("read" or "write")
        :param ttl: Time-to-live in seconds for the access link
        :return: Tuple of (urls, matched_paths)
        :raises ValueError: If method is unsupported or resource invalid
        """
        if method not in ["read", "write"]:
            raise ValueError(f"Unsupported method {method!r}")

        # WRITE: single path
        if method == "write":
            # Validate path security
            try:
                abs_path = self._validate_path(resource)
            except ValueError as e:
                raise ValueError(f"Invalid write path: {e}")

            # Phase 1: Return placeholder URL
            # Phase 4 will call: POST {issuer_url}/v1/presign
            placeholder_url = f"{self.instance_url}/{resource}?method=write&ttl={ttl}"
            logger.info(f"generate_access_link (write): placeholder URL for {resource}")
            return [placeholder_url], [resource]

        # READ: treat resource as regex pattern, match against file tree
        try:
            pattern = re.compile(resource)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

        # Get all paths from file tree (excluding root)
        all_paths = [
            n.identifier
            for n in self.file_tree.all_nodes()
            if n.identifier != 'root'
        ]

        # Match paths using fullmatch (like S3 agent)
        matched = [p for p in all_paths if pattern.fullmatch(p)]

        if not matched:
            logger.info(f"No paths match regex: {resource}")
            return [], []

        # Validate all matched paths are safe
        try:
            for path in matched:
                self._validate_path(path)
        except ValueError as e:
            raise ValueError(f"Matched path validation failed: {e}")

        # Phase 1: Generate placeholder URLs
        # Phase 4 will call: POST {issuer_url}/v1/presign for each path
        urls = [
            f"{self.instance_url}/{path}?method=read&ttl={ttl}"
            for path in matched
        ]

        logger.info(f"generate_access_link (read): matched {len(matched)} for {resource}")
        return urls, matched

    def config(self, secrets: bool = False) -> dict:
        """
        Return agent configuration.

        :param secrets: Whether to include sensitive information
        :return: Configuration dictionary
        """
        base_config = super().config(secrets)
        base_config['root_path'] = str(self.root_path)
        return base_config

    def _secrets(self) -> dict:
        """
        Return secrets for this agent.
        POSIX agent has no credentials in Phase 1.
        Future phases may include service account tokens.

        :return: Empty dict (no secrets in Phase 1)
        """
        return {}

    def refresh_connection(self):
        """
        Refresh the agent's connection to the storage backend.
        For POSIX filesystem, this reloads the file tree.
        """
        logger.info("Refreshing POSIX file tree")
        self._load_file_tree()

    def close(self):
        """
        Perform cleanup of resources.
        POSIX agent has no persistent connections to close in Phase 1.
        """
        logger.info("Closing POSIX agent")
        pass

    def __str__(self):
        return f"PosixStorageAgent(root_path={self.root_path}, instance_url={self.instance_url})"
