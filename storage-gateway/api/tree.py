"""
File Tree API Endpoint

Returns a list of all files in the storage root.
This allows the backend to discover what files are available
without knowing the storage server's directory structure.
"""
import os
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import List

logger = logging.getLogger('storage-gateway.api.tree')

router = APIRouter(prefix='/api', tags=["tree"])

# Global variables set during initialization
_root_path: Path = None


def init_tree_endpoint(root_path: str):
    """
    Initialize the tree endpoint with root path configuration.

    :param root_path: Absolute path to storage root directory
    """
    global _root_path
    _root_path = Path(root_path).resolve()
    logger.info(f"Tree endpoint initialized with root: {_root_path}")


@router.get("/tree")
async def get_file_tree() -> dict:
    """
    Get list of all files in storage.

    Returns relative paths only (no absolute paths exposed).
    The Gateway controls what's visible based on its root_path configuration.

    Returns:
        dict: {"files": [list of relative file paths]}
    """
    if _root_path is None:
        raise HTTPException(status_code=500, detail="Tree endpoint not initialized")

    if not _root_path.exists():
        raise HTTPException(status_code=500, detail="Storage root path does not exist")

    if not _root_path.is_dir():
        raise HTTPException(status_code=500, detail="Storage root path is not a directory")

    try:
        files = []

        # Walk the filesystem starting from root_path
        for root_dir, dirs, filenames in os.walk(_root_path):
            # Get path relative to storage root
            rel_root = Path(root_dir).relative_to(_root_path)

            # Add all files in this directory
            for filename in filenames:
                if rel_root == Path('.'):
                    # Files directly in root
                    file_path = filename
                else:
                    # Files in subdirectories - use forward slash separator
                    file_path = f"{str(rel_root).replace(os.sep, '/')}/{filename}"

                files.append(file_path)

            # Add directories (even if empty)
            for dir_name in dirs:
                if rel_root == Path('.'):
                    dir_path = dir_name
                else:
                    dir_path = f"{str(rel_root).replace(os.sep, '/')}/{dir_name}"

                files.append(dir_path)

        logger.debug(f"Returning {len(files)} files/directories from tree")
        return {"files": files}

    except Exception as e:
        logger.error(f"Error generating file tree: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate file tree: {str(e)}")
