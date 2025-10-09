import os
import re
import logging
import treelib
import requests
from typing import List, Tuple, Optional
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
        "root_path": str,          # Absolute path to storage root
        "issuer_url": str,          # Storage Issuer service URL
        "issuer_api_key": str,      # API key for Issuer authentication
        "instance_uuid": str,       # Instance UUID for policy tracking
    }

    def __init__(
        self,
        instance_url: str,
        root_path: str,
        issuer_url: str,
        issuer_api_key: str,
        instance_uuid: str
    ):
        """
        Initialize POSIX storage agent.

        :param instance_url: Gateway service URL for file downloads
        :param root_path: Absolute path to the storage root directory
        :param issuer_url: Storage Issuer service URL for JWT generation
        :param issuer_api_key: API key for Issuer authentication
        :param instance_uuid: Instance UUID for policy tracking
        :raises ValueError: If root_path doesn't exist or isn't a directory
        """
        super().__init__(instance_url)

        self.issuer_url = issuer_url
        self.issuer_api_key = issuer_api_key
        self.instance_uuid = instance_uuid

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

    def _call_issuer(self, user_uuid: str, path: str, op: str, ttl: int) -> dict:
        """
        Call the Storage Issuer service to generate a JWT presigned URL.

        :param user_uuid: User UUID for token generation
        :param path: Resource path
        :param op: Operation ("read" or "write")
        :param ttl: Time-to-live in seconds
        :return: Response dict with 'token', 'download_url', 'expires_at'
        :raises requests.RequestException: If API call fails
        """
        url = f"{self.issuer_url}/v1/presign"
        headers = {
            "X-API-Key": self.issuer_api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "user_uuid": user_uuid,
            "instance_uuid": self.instance_uuid,
            "path": path,
            "op": op,
            "ttl": ttl,
            "bundle": "file"
        }

        logger.debug(f"Calling Issuer: {url} with path={path}, op={op}")
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()

        return response.json()

    def generate_access_link(
        self, resource: str, method: str, ttl: int, user_uuid: str
    ) -> Tuple[List[str], List[str]]:
        """
        Generate access links for POSIX resources.

        Calls the Storage Issuer service to generate JWT presigned URLs.

        :param resource: Resource path or regex pattern
        :param method: Access method ("read" or "write")
        :param ttl: Time-to-live in seconds for the access link
        :param user_uuid: User UUID for token generation
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

            # Call Issuer to generate JWT token
            try:
                token_response = self._call_issuer(
                    user_uuid=user_uuid,
                    path=resource,
                    op="write",
                    ttl=ttl
                )
                download_url = token_response['download_url']
                logger.info(f"generate_access_link (write): generated JWT for {resource}")
                return [download_url], [resource]
            except Exception as e:
                logger.error(f"Failed to generate write token for {resource}: {e}")
                raise ValueError(f"Token generation failed: {e}")

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

        # Generate JWT tokens for all matched paths
        urls = []
        for path in matched:
            try:
                token_response = self._call_issuer(
                    user_uuid=user_uuid,
                    path=path,
                    op="read",
                    ttl=ttl
                )
                urls.append(token_response['download_url'])
            except Exception as e:
                logger.error(f"Failed to generate read token for {path}: {e}")
                raise ValueError(f"Token generation failed for {path}: {e}")

        logger.info(f"generate_access_link (read): generated {len(urls)} JWTs for {resource}")
        return urls, matched

    def config(self, secrets: bool = False) -> dict:
        """
        Return agent configuration.

        :param secrets: Whether to include sensitive information
        :return: Configuration dictionary
        """
        base_config = super().config(secrets)
        base_config['root_path'] = str(self.root_path)
        base_config['issuer_url'] = self.issuer_url
        base_config['instance_uuid'] = self.instance_uuid
        return base_config

    def _secrets(self) -> dict:
        """
        Return secrets for this agent.

        :return: Dictionary containing issuer_api_key
        """
        return {
            'issuer_api_key': self.issuer_api_key
        }

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
        return (f"PosixStorageAgent(root_path={self.root_path}, "
                f"instance_url={self.instance_url}, issuer_url={self.issuer_url})")
