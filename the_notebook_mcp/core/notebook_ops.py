"""
Core notebook file operations (read, write, validate path).

These functions are designed to be independent of global state and
receive necessary configuration (like allowed roots) explicitly.
"""

import os
from typing import List

import nbformat
from loguru import logger


def is_path_allowed(target_path: str, allowed_roots: List[str]) -> bool:
    """Checks if the target path is within one of the allowed roots."""
    if not allowed_roots:
        logger.warning("Security check skipped: No allowed roots configured.")
        return False

    try:
        # Ensure target_path is absolute and resolved
        abs_target_path = os.path.realpath(target_path)
    except Exception as e:
        logger.error(f"Error resolving path '{target_path}': {e}")
        return False

    for allowed_root in allowed_roots:
        try:
            # Ensure allowed_root is also absolute and resolved
            abs_allowed_root = os.path.realpath(allowed_root)
            if abs_target_path.startswith(abs_allowed_root + os.sep) or abs_target_path == abs_allowed_root:
                logger.trace(f"Path '{abs_target_path}' allowed within root '{abs_allowed_root}'")
                return True
        except Exception as e:
            logger.error(f"Error resolving allowed root '{allowed_root}': {e}")
            continue

    logger.warning(f"Security check failed: Path '{abs_target_path}' is outside allowed roots: {allowed_roots}")
    return False


async def read_notebook(
    notebook_path: str,
    allowed_roots: List[str],
) -> nbformat.NotebookNode:
    """Reads a notebook file safely, ensuring it's within allowed roots."""
    if not os.path.isabs(notebook_path):
        logger.error(f"Security Risk: Received non-absolute path: {notebook_path}")
        raise ValueError("Invalid notebook path: Only absolute paths are allowed.")

    if not is_path_allowed(notebook_path, allowed_roots):
        raise PermissionError(f"Access denied: Path '{notebook_path}' is outside the allowed workspace roots.")

    if not notebook_path.endswith(".ipynb"):
        raise ValueError(f"Invalid file type: '{notebook_path}' must point to a .ipynb file.")

    resolved_path = os.path.realpath(notebook_path)
    if not os.path.isfile(resolved_path):
        raise FileNotFoundError(f"Notebook file not found at: {resolved_path}")

    try:
        logger.debug(f"Reading notebook from: {resolved_path}")

        with open(resolved_path, "r", encoding="utf-8") as f:
            nb = nbformat.read(f, as_version=4)
        logger.debug(f"Successfully read notebook: {resolved_path}")
        return nb
    except Exception as e:
        logger.error(f"Error reading notebook {resolved_path}: {e}", exc_info=True)
        raise IOError(f"Failed to read notebook file '{resolved_path}': {e}") from e


async def write_notebook(
    notebook_path: str,
    nb_node: nbformat.NotebookNode,
    allowed_roots: List[str],
    max_notebook_size: int = 10 * 1024 * 1024,  # Default 10MB, should come from config eventually
):
    """Writes a notebook node to a file safely."""
    if not os.path.isabs(notebook_path):
        logger.error(f"Security Risk: Received non-absolute path for writing: {notebook_path}")
        raise ValueError("Invalid notebook path: Only absolute paths are allowed for writing.")

    if not is_path_allowed(notebook_path, allowed_roots):
        raise PermissionError(
            f"Access denied: Path '{notebook_path}' is outside the allowed workspace roots for writing."
        )

    if not notebook_path.endswith(".ipynb"):
        raise ValueError(f"Invalid file type: '{notebook_path}' must point to a .ipynb file for writing.")

    resolved_path = os.path.realpath(notebook_path)

    try:
        notebook_string = nbformat.writes(nb_node, version=nbformat.NO_CONVERT)
        if len(notebook_string.encode("utf-8")) > max_notebook_size:
            raise ValueError(
                f"Notebook content size ({len(notebook_string.encode('utf-8'))} bytes) exceeds maximum allowed size ({max_notebook_size} bytes)."
            )

        logger.debug(f"Writing notebook to: {resolved_path}")
        with open(resolved_path, "w", encoding="utf-8") as f:
            nbformat.write(nb_node, f)
        logger.debug(f"Successfully wrote notebook: {resolved_path}")
    except Exception as e:
        logger.error(f"Error writing notebook {resolved_path}: {e}", exc_info=True)
        raise IOError(f"Failed to write notebook file '{resolved_path}': {e}") from e
