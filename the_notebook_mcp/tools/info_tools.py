import os
from typing import List, Dict, Union

import nbformat
from loguru import logger

from ..core import notebook_ops
from ..core.config import ServerConfig
from .tool_utils import (
    extract_code_outline,
    extract_markdown_outline,
    get_first_line_context,
)


class InfoToolsProvider:
    """Provides MCP tools for reading notebook information and content."""

    def __init__(self, config: ServerConfig):
        self.config = config
        # Directly use imported notebook_ops functions
        self.read_notebook = notebook_ops.read_notebook
        self.is_path_allowed = notebook_ops.is_path_allowed
        logger.debug("InfoToolsProvider initialized.")

    async def notebook_read(self, notebook_path: str) -> dict:
        """Reads the entire content of a Jupyter Notebook file.

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.

        Returns:
            A dictionary representing the notebook content (nbformat structure).
        """
        logger.debug(f"[Tool: notebook_read] Called. Args: path={notebook_path}")
        try:
            # Security check happens within read_notebook
            nb = await self.read_notebook(notebook_path, self.config.allow_root_dirs)

            # --- Size Check (Optional, but good practice) ---
            # Example: Check total notebook size if needed, though read_notebook might handle internal limits.
            # Consider if nbformat.writes(nb) size check is necessary based on config

            logger.info(
                f"[Tool: notebook_read] SUCCESS - Read notebook content for {notebook_path}.",
                tool_success=True,
            )
            # Return the notebook object directly (nbformat handles JSON compatibility)
            return nb

        except (
            PermissionError,
            FileNotFoundError,
            ValueError,
            nbformat.validator.ValidationError,
            IOError,
        ) as e:
            logger.error(f"[Tool: notebook_read] FAILED - {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_read] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred while reading the notebook: {e}") from e

    async def notebook_read_cell(self, notebook_path: str, cell_index: int) -> str:
        """Reads the source content of a specific cell in a Jupyter Notebook.

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.
            cell_index: The 0-based index of the cell to read.

        Returns:
            The source content (string) of the specified cell.
        """
        logger.debug(f"[Tool: notebook_read_cell] Called. Args: path={notebook_path}, index={cell_index}")
        try:
            nb = await self.read_notebook(notebook_path, self.config.allow_root_dirs)
            if not 0 <= cell_index < len(nb.cells):
                raise IndexError(f"Cell index {cell_index} is out of bounds (0-{len(nb.cells) - 1}).")

            cell = nb.cells[cell_index]
            source = cell.get("source", "")

            # Optional: Validate source size on read? Usually done on write.
            # if len(source.encode('utf-8')) > self.config.max_cell_source_size:
            #     logger.warning(f"[Tool: notebook_read_cell] Cell source size exceeds limit, but returning content.")

            logger.info(
                f"[Tool: notebook_read_cell] SUCCESS - Read cell {cell_index} source from {notebook_path}.",
                tool_success=True,
            )
            return source

        except (
            PermissionError,
            FileNotFoundError,
            IndexError,
            ValueError,
            nbformat.validator.ValidationError,
            IOError,
        ) as e:
            logger.error(f"[Tool: notebook_read_cell] FAILED - {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_read_cell] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred while reading cell {cell_index}: {e}") from e

    async def notebook_get_cell_count(self, notebook_path: str) -> int:
        """Gets the total number of cells in a Jupyter Notebook.

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.

        Returns:
            The integer count of cells in the notebook.
        """
        logger.debug(f"[Tool: notebook_get_cell_count] Called. Args: path={notebook_path}")
        try:
            nb = await self.read_notebook(notebook_path, self.config.allow_root_dirs)
            count = len(nb.cells)
            logger.info(
                f"[Tool: notebook_get_cell_count] SUCCESS - Notebook {notebook_path} has {count} cells.",
                tool_success=True,
            )
            return count
        except (
            PermissionError,
            FileNotFoundError,
            ValueError,
            nbformat.validator.ValidationError,
            IOError,
        ) as e:
            logger.error(f"[Tool: notebook_get_cell_count] FAILED - {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_get_cell_count] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred while getting cell count: {e}") from e

    async def notebook_get_info(self, notebook_path: str) -> dict:
        """Gets basic information about a Jupyter Notebook file.

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.

        Returns:
            A dictionary containing basic file info (path, size, modified time)
            and notebook info (cell count, format version).
        """
        logger.debug(f"[Tool: notebook_get_info] Called. Args: path={notebook_path}")
        try:
            # Basic path validation first
            if not os.path.isabs(notebook_path):
                raise ValueError("Invalid notebook path: Only absolute paths are allowed.")
            if not self.is_path_allowed(notebook_path, self.config.allow_root_dirs):
                raise PermissionError("Access denied: Path is outside the allowed workspace roots.")
            if not notebook_path.endswith(".ipynb"):
                raise ValueError("Invalid file type: Path must point to a .ipynb file.")

            resolved_path = os.path.realpath(notebook_path)
            if not os.path.isfile(resolved_path):
                raise FileNotFoundError(f"Notebook file not found at: {resolved_path}")

            # Get file stats
            file_stat = os.stat(resolved_path)
            file_info = {
                "path": notebook_path,  # Return original path requested
                "resolved_path": resolved_path,
                "size_bytes": file_stat.st_size,
                "last_modified": file_stat.st_mtime,
            }

            # Read notebook for cell count and format info
            nb = await self.read_notebook(notebook_path, self.config.allow_root_dirs)
            notebook_info = {
                "cell_count": len(nb.cells),
                "nbformat": nb.nbformat,
                "nbformat_minor": nb.nbformat_minor,
                "metadata_keys": list(nb.metadata.keys()),  # List top-level metadata keys
            }

            info = {**file_info, **notebook_info}
            logger.info(
                f"[Tool: notebook_get_info] SUCCESS - Gathered notebook info for {notebook_path}.",
                tool_success=True,
            )
            return info

        except (
            PermissionError,
            FileNotFoundError,
            ValueError,
            nbformat.validator.ValidationError,
            IOError,
            OSError,
        ) as e:
            logger.error(f"[Tool: notebook_get_info] FAILED - {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_get_info] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred while getting notebook info: {e}") from e

    async def notebook_get_outline(self, notebook_path: str) -> List[Dict[str, Union[int, str, List[str]]]]:
        """Generates a structural outline of the notebook (headings, function/class definitions).

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.

        Returns:
            A list of dictionaries, where each dictionary represents an outline item
            (e.g., {'level': 1, 'text': 'Section Heading', 'cell_index': 0, 'type': 'markdown'}).
            For code cells, 'text' might be a function/class name or first line context,
            and 'definitions' might contain a list of extracted names.
        """
        logger.debug(f"[Tool: notebook_get_outline] Called. Args: path={notebook_path}")
        outline = []
        try:
            nb = await self.read_notebook(notebook_path, self.config.allow_root_dirs)
            for i, cell in enumerate(nb.cells):
                source = cell.get("source", "")
                cell_type = cell.cell_type

                if cell_type == "markdown":
                    markdown_headings = extract_markdown_outline(source)
                    for level, text in markdown_headings:
                        outline.append(
                            {
                                "level": level,
                                "text": text,
                                "cell_index": i,
                                "type": "markdown_heading",
                            }
                        )
                elif cell_type == "code":
                    code_defs = extract_code_outline(source)
                    first_lines = get_first_line_context(source)

                    # Decide what to represent the code cell as in the outline
                    # Option 1: Primary entry for the cell with definitions listed
                    # Option 2: Separate entry for each major definition (can be noisy)

                    # Using Option 1: Single entry for the code cell
                    if code_defs or first_lines:  # Only add if there's something interesting
                        # Use the first definition or first line as the main text
                        main_text = code_defs[0] if code_defs else first_lines[0]
                        outline.append(
                            {
                                "level": 0,  # Or some indicator that it's code
                                "text": main_text.strip(),
                                "cell_index": i,
                                "type": "code",
                                "definitions": code_defs,  # List function/class names found
                                "context": first_lines,  # Include first few lines for context
                            }
                        )

            logger.info(
                f"[Tool: notebook_get_outline] SUCCESS - Generated outline with {len(outline)} items for {notebook_path}.",
                tool_success=True,
            )
            return outline

        except (
            PermissionError,
            FileNotFoundError,
            ValueError,
            nbformat.validator.ValidationError,
            IOError,
        ) as e:
            logger.error(f"[Tool: notebook_get_outline] FAILED - {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_get_outline] FAILED - Unexpected error generating outline: {e}")
            raise RuntimeError(f"An unexpected error occurred while generating the notebook outline: {e}") from e

    async def notebook_search(
        self, notebook_path: str, query: str, case_sensitive: bool = False
    ) -> List[Dict[str, Union[int, str]]]:
        """Searches for a string within the source of all cells in a notebook.

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.
            query: The string to search for.
            case_sensitive: Whether the search should be case-sensitive (default: False).

        Returns:
            A list of dictionaries, each representing a match, containing:
            {'cell_index': int, 'cell_type': str, 'line_number': int, 'line_content': str}.
        """
        logger.debug(
            f"[Tool: notebook_search] Called. Args: path={notebook_path}, query_len={len(query)}, case_sensitive={case_sensitive}"
        )
        matches = []
        try:
            nb = await self.read_notebook(notebook_path, self.config.allow_root_dirs)
            search_query = query if case_sensitive else query.lower()

            for i, cell in enumerate(nb.cells):
                source = cell.get("source", "")
                cell_type = cell.cell_type
                lines = source.splitlines()

                for line_num, line in enumerate(lines):
                    line_to_search = line if case_sensitive else line.lower()
                    if search_query in line_to_search:
                        matches.append(
                            {
                                "cell_index": i,
                                "cell_type": cell_type,
                                "line_number": line_num + 1,  # 1-based line number
                                "line_content": line,  # Return original line
                            }
                        )
                        # Optimization: Stop after N matches? Configurable limit?
                        # if len(matches) >= MAX_SEARCH_RESULTS: break
                # if len(matches) >= MAX_SEARCH_RESULTS: break

            logger.info(
                f"[Tool: notebook_search] SUCCESS - Found {len(matches)} matches in {notebook_path}.",
                tool_success=True,
            )
            return matches

        except (
            PermissionError,
            FileNotFoundError,
            ValueError,
            nbformat.validator.ValidationError,
            IOError,
        ) as e:
            logger.error(f"[Tool: notebook_search] FAILED - {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_search] FAILED - Unexpected error during search: {e}")
            raise RuntimeError(f"An unexpected error occurred while searching the notebook: {e}") from e
