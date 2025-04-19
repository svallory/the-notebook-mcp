"""
Core notebook file operations (read, write, validate path).

These functions are designed to be independent of global state and 
receive necessary configuration (like allowed roots) explicitly.
"""

import os
import logging
from typing import List

import nbformat

logger = logging.getLogger(__name__)

def is_path_allowed(target_path: str, allowed_roots: List[str]) -> bool:
    """Checks if the target path is within one of the allowed roots."""
    if not allowed_roots:
        logger.warning("Security check skipped: No allowed roots configured.")
        return False # Or True? Defaulting to False for safety.

    try:
        # Ensure target_path is absolute and resolved
        abs_target_path = os.path.realpath(target_path)
    except Exception as e:
        logger.error(f"Error resolving path '{target_path}': {e}")
        return False # Cannot validate unresolved path

    for allowed_root in allowed_roots:
        try:
            # Ensure allowed_root is also absolute and resolved
            abs_allowed_root = os.path.realpath(allowed_root)
            if abs_target_path.startswith(abs_allowed_root + os.sep) or abs_target_path == abs_allowed_root:
                # os.path.commonpath might be another option but startswith is often clearer
                return True
        except Exception as e:
            logger.error(f"Error resolving allowed root '{allowed_root}': {e}")
            continue # Try the next root

    return False

async def read_notebook(
    notebook_path: str,
    allowed_roots: List[str],
) -> nbformat.NotebookNode:
    """Reads a notebook file safely, ensuring it's within allowed roots."""
    if not os.path.isabs(notebook_path):
        # Log the attempt, but raise ValueError as the contract requires absolute paths
        logger.error(f"Security Risk: Received non-absolute path: {notebook_path}")
        raise ValueError("Invalid notebook path: Only absolute paths are allowed.")

    # Core Security Check: Validate against allowed roots
    if not is_path_allowed(notebook_path, allowed_roots):
        logger.error(f"Security Violation: Attempted access outside allowed roots: {notebook_path}")
        raise PermissionError(f"Access denied: Path '{notebook_path}' is outside the allowed workspace roots.")

    # Basic check for .ipynb extension
    if not notebook_path.endswith(".ipynb"):
         raise ValueError(f"Invalid file type: '{notebook_path}' must point to a .ipynb file.")

    # Use the resolved path for file system operations
    resolved_path = os.path.realpath(notebook_path)
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"Notebook file not found at: {resolved_path}")

    try:
        logger.debug(f"Reading notebook from: {resolved_path}")
        # Read using the resolved path
        # Consider adding encoding='utf-8' explicitly
        nb = nbformat.read(resolved_path, as_version=4)
        logger.debug(f"Successfully read notebook: {resolved_path}")
        return nb
    except Exception as e:
        logger.error(f"Error reading notebook {resolved_path}: {e}", exc_info=True)
        raise IOError(f"Failed to read notebook file '{resolved_path}': {e}") from e

async def write_notebook(
    notebook_path: str,
    nb: nbformat.NotebookNode,
    allowed_roots: List[str],
):
    """Writes a notebook file safely, ensuring it's within allowed roots."""
    if not os.path.isabs(notebook_path):
         logger.error(f"Security Risk: Received non-absolute path for writing: {notebook_path}")
         raise ValueError("Invalid notebook path: Only absolute paths are allowed for writing.")

    # Core Security Check: Validate against allowed roots
    if not is_path_allowed(notebook_path, allowed_roots):
         logger.error(f"Security Violation: Attempted write outside allowed roots: {notebook_path}")
         raise PermissionError(f"Access denied: Path '{notebook_path}' is outside the allowed workspace roots.")

    # Use the resolved path for file system operations
    resolved_path = os.path.realpath(notebook_path)
    if not resolved_path.endswith(".ipynb"):
         raise ValueError(f"Invalid file type for writing: '{resolved_path}' must point to a .ipynb file.")

    # Ensure parent directory exists
    parent_dir = os.path.dirname(resolved_path)
    try:
        if not os.path.isdir(parent_dir):
            logger.info(f"Creating parent directory: {parent_dir}")
            os.makedirs(parent_dir, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create parent directory '{parent_dir}': {e}")
        raise IOError(f"Could not create directory for notebook '{resolved_path}': {e}") from e

    try:
        logger.debug(f"Writing notebook to: {resolved_path}")
        # Consider adding encoding='utf-8' explicitly
        nbformat.write(nb, resolved_path)
        logger.debug(f"Successfully wrote notebook: {resolved_path}")
    except Exception as e:
        logger.error(f"Error writing notebook {resolved_path}: {e}", exc_info=True)
        raise IOError(f"Failed to write notebook file '{resolved_path}': {e}") from e 