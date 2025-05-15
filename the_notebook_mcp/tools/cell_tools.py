"""
Tools for cell manipulation (add, edit, delete, move, split, merge, type change, duplicate).
"""

import copy
from typing import List, Dict, Tuple
from loguru import logger
import os

import nbformat

from ..core.config import ServerConfig
from ..core import notebook_ops

from jupyter_kernel_client import KernelClient
from jupyter_nbmodel_client import (
    NbModelClient,
    get_jupyter_notebook_websocket_url,
)


class CellToolsProvider:
    def __init__(self, config: ServerConfig):
        self.config = config
        logger.debug("CellToolsProvider initialized.")
        # Dictionary to cache kernel clients for notebook paths
        # Keys are tuples of (notebook_path, server_url, token)
        # Values are KernelClient instances
        self._kernel_cache: Dict[Tuple[str, str, str], KernelClient] = {}

    async def notebook_edit_cell(self, notebook_path: str, cell_index: int, source: str) -> str:
        """Replaces the source content of a specific cell in a Jupyter Notebook.

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.
            cell_index: The 0-based index of the cell to edit.
            source: The new source code or markdown content for the cell.
        """
        logger.debug(
            f"[Tool: notebook_edit_cell] Called. Args: path={notebook_path}, index={cell_index}, source_len={len(source)}"
        )
        try:
            # Validate source size
            if len(source.encode("utf-8")) > self.config.max_cell_source_size:
                raise ValueError(
                    f"Source content exceeds maximum allowed size ({self.config.max_cell_source_size} bytes)."
                )

            nb = await notebook_ops.read_notebook(notebook_path, self.config.allow_root_dirs)
            if not 0 <= cell_index < len(nb.cells):
                raise IndexError(f"Cell index {cell_index} is out of bounds (0-{len(nb.cells) - 1}).")

            nb.cells[cell_index].source = source
            await notebook_ops.write_notebook(notebook_path, nb, self.config.allow_root_dirs)
            logger.info(
                f"[Tool: notebook_edit_cell] SUCCESS - Edited cell {cell_index}.",
                tool_success=True,
            )
            return f"Successfully edited cell {cell_index} in {notebook_path}"
        except (
            ValueError,
            FileNotFoundError,
            IndexError,
            IOError,
            PermissionError,
            nbformat.validator.ValidationError,
        ) as e:
            logger.error(f"[Tool: notebook_edit_cell] FAILED - Specific error: {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_edit_cell] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred: {e}") from e

    async def notebook_add_cell(self, notebook_path: str, cell_type: str, source: str, insert_after_index: int) -> str:
        """Adds a new cell to a Jupyter Notebook after the specified index.

        Args:
            notebook_path: Absolute path to the .ipynb file.
            cell_type: Type of cell ('code' or 'markdown'). Must be lowercase.
            source: The source code or markdown content for the new cell.
            insert_after_index: The 0-based index after which to insert the new cell (-1 to insert at the beginning).
        """
        logger.debug(
            f"[Tool: notebook_add_cell] Called. Args: path={notebook_path}, type={cell_type}, after_index={insert_after_index}, source_len={len(source)}"
        )
        try:
            # Validate source size
            if len(source.encode("utf-8")) > self.config.max_cell_source_size:
                raise ValueError(
                    f"Source content exceeds maximum allowed size ({self.config.max_cell_source_size} bytes)."
                )

            nb = await notebook_ops.read_notebook(notebook_path, self.config.allow_root_dirs)

            if cell_type == "code":
                new_cell = nbformat.v4.new_code_cell(source)
            elif cell_type == "markdown":
                new_cell = nbformat.v4.new_markdown_cell(source)
            else:
                raise ValueError("Invalid cell_type: Must be 'code' or 'markdown'.")

            insertion_index = insert_after_index + 1
            if not 0 <= insertion_index <= len(nb.cells):
                raise IndexError(
                    f"Insertion index {insertion_index} (based on insert_after_index {insert_after_index}) is out of bounds (0-{len(nb.cells)})."
                )

            nb.cells.insert(insertion_index, new_cell)
            await notebook_ops.write_notebook(notebook_path, nb, self.config.allow_root_dirs)
            logger.info(
                f"[Tool: notebook_add_cell] SUCCESS - Added {cell_type} cell at index {insertion_index}.",
                tool_success=True,
            )
            return f"Successfully added {cell_type} cell at index {insertion_index} in {notebook_path}"
        except (
            ValueError,
            FileNotFoundError,
            IndexError,
            IOError,
            PermissionError,
            nbformat.validator.ValidationError,
        ) as e:
            logger.error(f"[Tool: notebook_add_cell] FAILED - Specific error: {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_add_cell] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred: {e}") from e

    async def notebook_delete_cell(self, notebook_path: str, cell_index: int) -> str:
        """Deletes a specific cell from a Jupyter Notebook.

        Args:
            notebook_path: Absolute path to the .ipynb file.
            cell_index: The 0-based index of the cell to delete.
        """
        logger.debug(f"[Tool: notebook_delete_cell] Called. Args: path={notebook_path}, index={cell_index}")
        try:
            nb = await notebook_ops.read_notebook(notebook_path, self.config.allow_root_dirs)
            if not 0 <= cell_index < len(nb.cells):
                raise IndexError(f"Cell index {cell_index} is out of bounds (0-{len(nb.cells) - 1}).")

            del nb.cells[cell_index]
            await notebook_ops.write_notebook(notebook_path, nb, self.config.allow_root_dirs)
            logger.info(
                f"[Tool: notebook_delete_cell] SUCCESS - Deleted cell {cell_index}.",
                tool_success=True,
            )
            return f"Successfully deleted cell {cell_index} from {notebook_path}"
        except (
            ValueError,
            FileNotFoundError,
            IndexError,
            IOError,
            PermissionError,
            nbformat.validator.ValidationError,
        ) as e:
            logger.error(f"[Tool: notebook_delete_cell] FAILED - Specific error: {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_delete_cell] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred: {e}") from e

    async def notebook_move_cell(self, notebook_path: str, from_index: int, to_index: int) -> str:
        """Moves a cell from one position to another.

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.
            from_index: The 0-based index of the cell to move.
            to_index: The 0-based target index where the cell should be moved to.
                      Note: This is the index after the move operation is complete.

        Returns:
            A success message string.
        """
        logger.debug(f"[Tool: notebook_move_cell] Called. Args: path={notebook_path}, from={from_index}, to={to_index}")
        try:
            nb = await notebook_ops.read_notebook(notebook_path, self.config.allow_root_dirs)
            num_cells = len(nb.cells)

            if not 0 <= from_index < num_cells:
                raise IndexError(f"Source index {from_index} is out of bounds (0-{num_cells - 1}).")
            # Allow moving to the very end (index == num_cells)
            if not 0 <= to_index <= num_cells:
                raise IndexError(f"Destination index {to_index} is out of bounds (0-{num_cells}).")

            # No change if indices are the same
            if from_index == to_index:
                logger.debug("[Tool: notebook_move_cell] SKIPPED - Cell move results in no change.")
                return f"Cell at index {from_index} was not moved (source and destination are the same)."

            # Remove the cell from its current position
            cell_to_move = nb.cells.pop(from_index)

            # Insert at the target index
            # If we're moving to the end of the notebook, we need to handle that case
            # If from_index < to_index, we need to account for the removal of the cell
            insert_at = to_index if from_index >= to_index else to_index - 1
            nb.cells.insert(insert_at, cell_to_move)

            await notebook_ops.write_notebook(notebook_path, nb, self.config.allow_root_dirs)
            logger.info(
                f"[Tool: notebook_move_cell] SUCCESS - Moved cell from {from_index} to {to_index}.",
                tool_success=True,
            )
            return f"Successfully moved cell from index {from_index} to {to_index} in {notebook_path}"
        except (
            ValueError,
            FileNotFoundError,
            IndexError,
            IOError,
            PermissionError,
            nbformat.validator.ValidationError,
        ) as e:
            logger.error(f"[Tool: notebook_move_cell] FAILED - Specific error: {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_move_cell] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred: {e}") from e

    async def notebook_split_cell(self, notebook_path: str, cell_index: int, split_at_line: int) -> str:
        """Splits a cell into two at a specified line number.

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.
            cell_index: The 0-based index of the cell to split.
            split_at_line: The 1-based line number within the cell's source where the split
                           should occur. Lines before this number remain in the original cell,
                           lines from this number onward move to a new cell inserted immediately after.

        Returns:
            A success message string.
        """
        logger.debug(
            f"[Tool: notebook_split_cell] Called. Args: path={notebook_path}, index={cell_index}, line={split_at_line}"
        )
        try:
            # Load the notebook using notebook_ops
            nb = await notebook_ops.read_notebook(notebook_path, self.config.allow_root_dirs)
            if not 0 <= cell_index < len(nb.cells):
                raise IndexError(f"Cell index {cell_index} is out of bounds (0-{len(nb.cells) - 1}).")

            # Get the cell to split and its content
            cell_to_split = nb.cells[cell_index]
            source = cell_to_split.get("source", "")

            # Split source into lines while preserving line endings
            lines = source.splitlines(True)

            # Convert 1-based line number (user-friendly) to 0-based index (for Python slicing)
            split_index = split_at_line - 1

            # Validate split position is within bounds
            if not 0 < split_index < len(lines):
                raise ValueError(
                    f"Split line number {split_at_line} is out of bounds for cell with {len(lines)} lines."
                )

            # Create two separate content parts by slicing the lines list
            source_part1 = "".join(lines[:split_index])  # First part: lines before split point
            source_part2 = "".join(lines[split_index:])  # Second part: split point line and all lines after

            # Validate the size of both parts to ensure they don't exceed allowed limits
            max_size = self.config.max_cell_source_size
            if len(source_part1.encode("utf-8")) > max_size or len(source_part2.encode("utf-8")) > max_size:
                raise ValueError(
                    f"Resulting source content after split exceeds maximum allowed size ({max_size} bytes) for one or both cells."
                )

            # Update the original cell with just the first part
            cell_to_split.source = source_part1

            # If it's a code cell, clear outputs and execution count since content changed
            if cell_to_split.cell_type == "code":
                cell_to_split.outputs = []
                cell_to_split.execution_count = None

            # Create a new cell for the second part with the same metadata and type as original
            new_cell_metadata = copy.deepcopy(cell_to_split.metadata)

            # Create the appropriate type of new cell based on the original cell's type
            if cell_to_split.cell_type == "code":
                new_cell = nbformat.v4.new_code_cell(source=source_part2, metadata=new_cell_metadata)
            elif cell_to_split.cell_type == "markdown":
                new_cell = nbformat.v4.new_markdown_cell(source=source_part2, metadata=new_cell_metadata)
            else:  # Raw cell
                new_cell = nbformat.v4.new_raw_cell(source=source_part2, metadata=new_cell_metadata)

            # Insert the new cell immediately after the original cell
            nb.cells.insert(cell_index + 1, new_cell)

            # Save the modified notebook back to disk
            await notebook_ops.write_notebook(notebook_path, nb, self.config.allow_root_dirs)
            logger.info(
                f"[Tool: notebook_split_cell] SUCCESS - Split cell {cell_index} at line {split_at_line}.",
                tool_success=True,
            )
            return f"Successfully split cell {cell_index} at line {split_at_line}."

        except (
            PermissionError,
            FileNotFoundError,
            IndexError,
            ValueError,
            nbformat.validator.ValidationError,
            IOError,
        ) as e:
            logger.error(f"[Tool: notebook_split_cell] FAILED - {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_split_cell] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred while splitting cell {cell_index}: {e}") from e

    async def notebook_merge_cells(self, notebook_path: str, first_cell_index: int) -> str:
        """Merges a cell with the one immediately following it.

        The content of the second cell is appended to the first cell's content.
        The second cell is then deleted.
        Cells must be of the same type (code or markdown).
        Metadata from the first cell is kept; metadata from the second is discarded.
        Outputs/execution count of the first cell are cleared if it's a code cell.

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.
            first_cell_index: The 0-based index of the first cell in the pair to merge.
                              The cell at `first_cell_index + 1` will be merged into this one.

        Returns:
            A success message string.
        """
        logger.debug(f"[Tool: notebook_merge_cells] Called. Args: path={notebook_path}, index={first_cell_index}")
        try:
            nb = await notebook_ops.read_notebook(notebook_path, self.config.allow_root_dirs)
            if not 0 <= first_cell_index < len(nb.cells) - 1:
                raise IndexError(f"Invalid index {first_cell_index}: Cannot merge last cell or index out of bounds.")

            cell1 = nb.cells[first_cell_index]
            cell2 = nb.cells[first_cell_index + 1]

            if cell1.cell_type != cell2.cell_type:
                raise ValueError(f"Cannot merge cells of different types ({cell1.cell_type} and {cell2.cell_type}).")
            if cell1.cell_type not in ("code", "markdown"):
                raise ValueError(f"Merging is only supported for code and markdown cells (found {cell1.cell_type}).")

            source1 = cell1.get("source", "")
            source2 = cell2.get("source", "")

            separator = "\n"
            merged_source = source1 + separator + source2

            if len(merged_source.encode("utf-8")) > self.config.max_cell_source_size:
                raise ValueError(
                    f"Merged source content exceeds maximum allowed size ({self.config.max_cell_source_size} bytes)."
                )

            cell1.source = merged_source
            if cell1.cell_type == "code":
                cell1.outputs = []
                cell1.execution_count = None

            del nb.cells[first_cell_index + 1]

            await notebook_ops.write_notebook(notebook_path, nb, self.config.allow_root_dirs)
            logger.info(
                f"[Tool: notebook_merge_cells] SUCCESS - Merged cell {first_cell_index + 1} into cell {first_cell_index}.",
                tool_success=True,
            )
            return f"Successfully merged cell {first_cell_index + 1} into cell {first_cell_index}."

        except (
            PermissionError,
            FileNotFoundError,
            IndexError,
            ValueError,
            nbformat.validator.ValidationError,
            IOError,
        ) as e:
            logger.error(f"[Tool: notebook_merge_cells] FAILED - {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_merge_cells] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred while merging cells: {e}") from e

    async def notebook_change_cell_type(self, notebook_path: str, cell_index: int, new_type: str) -> str:
        """Changes the type of a specific cell (e.g., code to markdown).

        Preserves source content and metadata. Clears outputs/execution count if changing from code.

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.
            cell_index: The 0-based index of the cell to change.
            new_type: The target cell type ('code', 'markdown', or 'raw').

        Returns:
            A success message string.
        """
        logger.debug(
            f"[Tool: notebook_change_cell_type] Called. Args: path={notebook_path}, index={cell_index}, type={new_type}"
        )

        allowed_types = ("code", "markdown", "raw")
        if new_type not in allowed_types:
            raise ValueError(f"Invalid target cell type '{new_type}'. Must be one of {allowed_types}.")

        try:
            nb = await notebook_ops.read_notebook(notebook_path, self.config.allow_root_dirs)
            if not 0 <= cell_index < len(nb.cells):
                raise IndexError(f"Cell index {cell_index} is out of bounds (0-{len(nb.cells) - 1}).")

            original_cell = nb.cells[cell_index]
            original_type = original_cell.cell_type

            if original_type == new_type:
                logger.debug(
                    f"[Tool: notebook_change_cell_type] Cell is already of type '{new_type}'. No change needed."
                )
                return f"Cell {cell_index} is already of type '{new_type}'."

            source = original_cell.get("source", "")
            metadata = copy.deepcopy(original_cell.metadata)
            attachments = copy.deepcopy(original_cell.get("attachments", {}))

            if new_type == "code":
                new_cell = nbformat.v4.new_code_cell(source=source, metadata=metadata)
                if attachments:
                    logger.warning(
                        f"[Tool: notebook_change_cell_type] Discarding attachments when converting cell {cell_index} to code type."
                    )
            elif new_type == "markdown":
                new_cell = nbformat.v4.new_markdown_cell(source=source, metadata=metadata, attachments=attachments)
            else:  # new_type == 'raw'
                new_cell = nbformat.v4.new_raw_cell(source=source, metadata=metadata)
                if attachments:
                    new_cell["attachments"] = attachments

            nb.cells[cell_index] = new_cell

            await notebook_ops.write_notebook(notebook_path, nb, self.config.allow_root_dirs)
            logger.info(
                f"[Tool: notebook_change_cell_type] SUCCESS - Changed cell {cell_index} from '{original_type}' to '{new_type}'.",
                tool_success=True,
            )
            return f"Successfully changed cell {cell_index} to type '{new_type}'."

        except (
            PermissionError,
            FileNotFoundError,
            IndexError,
            ValueError,
            nbformat.validator.ValidationError,
            IOError,
        ) as e:
            logger.error(f"[Tool: notebook_change_cell_type] FAILED - {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_change_cell_type] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred while changing cell type: {e}") from e

    async def notebook_duplicate_cell(self, notebook_path: str, cell_index: int, count: int = 1) -> str:
        """Duplicates a cell one or more times, inserting the copies after the original cell.

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.
            cell_index: The 0-based index of the cell to duplicate.
            count: The number of copies to create (default: 1).

        Returns:
            A success message with the number of duplicated cells.
        """
        logger.debug(
            f"[Tool: notebook_duplicate_cell] Called. Args: path={notebook_path}, index={cell_index}, count={count}"
        )
        try:
            # Read existing notebook
            nb = await notebook_ops.read_notebook(notebook_path, self.config.allow_root_dirs)

            # Validate cell index
            if not 0 <= cell_index < len(nb.cells):
                raise IndexError(f"Cell index {cell_index} is out of bounds (0-{len(nb.cells) - 1}).")

            # Validate count
            if count < 1:
                raise ValueError("Count must be at least 1.")

            # Get the cell to duplicate
            source_cell = nb.cells[cell_index]

            # Create copies and insert right after the source cell
            import uuid
            import copy

            for i in range(count):
                # Deep copy to avoid shared references
                new_cell = copy.deepcopy(source_cell)

                # Add a fresh cell ID to avoid duplicates
                new_cell["id"] = str(uuid.uuid4())

                # If it's a code cell, clear execution outputs and count
                if new_cell.cell_type == "code":
                    new_cell["outputs"] = []
                    new_cell["execution_count"] = None

                # Insert the new cell after the original (and any previously inserted copies)
                insert_pos = cell_index + 1 + i
                nb.cells.insert(insert_pos, new_cell)

            # Write the modified notebook back
            await notebook_ops.write_notebook(notebook_path, nb, self.config.allow_root_dirs)

            logger.info(
                f"[Tool: notebook_duplicate_cell] SUCCESS - Duplicated cell {cell_index} {count} times in {notebook_path}.",
                tool_success=True,
            )
            return f"Successfully duplicated cell {cell_index} {count} times."

        except (
            PermissionError,
            FileNotFoundError,
            IndexError,
            ValueError,
            nbformat.validator.ValidationError,
            IOError,
        ) as e:
            logger.error(f"[Tool: notebook_duplicate_cell] FAILED - {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_duplicate_cell] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred while duplicating cells: {e}") from e

    async def notebook_execute_cell(
        self, notebook_path: str, cell_index: int, server_url: str = None, token: str = None
    ) -> List[dict]:
        """Executes a specific code cell and returns its outputs.

        Note: AI Assistants MUST ask the user for server_url and token values if they are not known,
        as these are required to connect to the Jupyter server that will execute the code.

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.
            cell_index: The 0-based index of the code cell to execute.
            server_url: URL of the Jupyter server (default: http://localhost:8888).
                        AI assistants should ask the user for this value.
            token: Jupyter server authentication token.
                   AI assistants should ask the user for this value.

        Returns:
            A list of dictionaries, where each dictionary represents an output
            (following the nbformat output structure).

        Raises:
            ValueError: If the cell is not a code cell or the server URL/token is invalid.
            IndexError: If the cell index is out of bounds.
            RuntimeError: For various execution failures.
        """
        logger.debug(
            f"[Tool: notebook_execute_cell] Called. Args: path={notebook_path}, "
            f"index={cell_index}, server_url={server_url}"
        )

        # Default server URL if not provided
        if not server_url:
            server_url = "http://localhost:8888"
        else:
            # Remove any trailing slashes
            server_url = server_url.rstrip("/")

        try:
            # Check if the path is allowed for security
            if not os.path.isabs(notebook_path):
                raise ValueError(f"Only absolute paths are allowed: {notebook_path}")

            if not notebook_ops.is_path_allowed(notebook_path, self.config.allow_root_dirs):
                raise PermissionError(f"Access denied: Path is outside the allowed workspace roots: {notebook_path}")

            # First, validate that the notebook path is allowed and the cell exists
            nb = await notebook_ops.read_notebook(notebook_path, self.config.allow_root_dirs)

            if not 0 <= cell_index < len(nb.cells):
                raise IndexError(f"Cell index {cell_index} is out of bounds (0-{len(nb.cells) - 1}).")

            cell = nb.cells[cell_index]
            if cell.cell_type != "code":
                raise ValueError(
                    f"Cell {cell_index} is not a code cell (type: {cell.cell_type}). Only code cells can be executed."
                )

            # Create a cache key for this notebook/server combination
            cache_key = (notebook_path, server_url, token)

            # Check if we already have a kernel client for this notebook
            if cache_key not in self._kernel_cache:
                logger.debug(f"[Tool: notebook_execute_cell] Creating new kernel client for {notebook_path}")
                try:
                    kernel = KernelClient(server_url=server_url, token=token)
                    kernel.start()
                    self._kernel_cache[cache_key] = kernel
                    logger.debug(f"[Tool: notebook_execute_cell] Kernel started successfully and cached")
                except Exception as e:
                    logger.error(f"[Tool: notebook_execute_cell] Failed to start kernel: {e}")
                    raise RuntimeError(f"Failed to connect to Jupyter kernel: {e}")
            else:
                logger.debug(f"[Tool: notebook_execute_cell] Using cached kernel for {notebook_path}")
                kernel = self._kernel_cache[cache_key]

            # Get the absolute path for the notebook to use with the websocket URL
            abs_notebook_path = os.path.abspath(notebook_path)
            notebook_relative_path = os.path.basename(abs_notebook_path)

            try:
                # Connect to the notebook
                websocket_url = get_jupyter_notebook_websocket_url(
                    server_url=server_url, token=token, path=notebook_relative_path
                )
                notebook = NbModelClient(websocket_url)
                await notebook.start()
                logger.debug(f"[Tool: notebook_execute_cell] Connected to notebook at {websocket_url}")

                try:
                    # Execute the cell
                    logger.debug(f"[Tool: notebook_execute_cell] Executing cell {cell_index}")
                    notebook.execute_cell(cell_index, kernel)

                    # Extract outputs
                    ydoc = notebook._doc
                    outputs = ydoc._ycells[cell_index]["outputs"]

                    # Process outputs to ensure they're serializable and handle size limits
                    processed_outputs = []
                    for output in outputs:
                        output_dict = dict(output)

                        # Handle large data similar to notebook_read_cell_output
                        if "data" in output_dict and isinstance(output_dict["data"], dict):
                            for mime_type, data_content in output_dict["data"].items():
                                if isinstance(data_content, str):
                                    if len(data_content.encode("utf-8")) > self.config.max_cell_output_size:
                                        if mime_type.startswith("image/"):
                                            output_dict["data"][mime_type] = (
                                                f"<image data too large: {len(data_content.encode('utf-8'))} bytes>"
                                            )
                                        else:
                                            output_dict["data"][mime_type] = (
                                                f"<data too large: {len(data_content.encode('utf-8'))} bytes, first 256 chars: {data_content[:256]}...>"
                                            )
                                        logger.warning(
                                            f"[Tool: notebook_execute_cell] Truncated large data for mime_type '{mime_type}' in cell {cell_index}."
                                        )

                        elif "text" in output_dict and isinstance(output_dict["text"], (str, list)):
                            text_content = output_dict["text"]
                            if isinstance(text_content, list):
                                text_content = "".join(text_content)

                            if len(text_content.encode("utf-8")) > self.config.max_cell_output_size:
                                output_dict["text"] = (
                                    f"<text data too large: {len(text_content.encode('utf-8'))} bytes, first 256 chars: {text_content[:256]}...>"
                                )
                                logger.warning(
                                    f"[Tool: notebook_execute_cell] Truncated large text output in cell {cell_index}."
                                )

                        processed_outputs.append(output_dict)

                    logger.info(
                        f"[Tool: notebook_execute_cell] SUCCESS - Executed cell {cell_index} and got {len(processed_outputs)} outputs.",
                        tool_success=True,
                    )
                    return processed_outputs
                finally:
                    # Always close the notebook client connection
                    # But keep the kernel running
                    if "notebook" in locals():
                        try:
                            await notebook.stop()
                        except Exception as e:
                            logger.error(f"[Tool: notebook_execute_cell] Error stopping notebook client: {e}")

            except Exception as e:
                logger.error(f"[Tool: notebook_execute_cell] Error during notebook execution: {e}")
                raise RuntimeError(f"Failed to execute notebook cell: {e}")

        except (
            PermissionError,
            FileNotFoundError,
            IndexError,
            ValueError,
            IOError,
        ) as e:
            logger.error(f"[Tool: notebook_execute_cell] FAILED - {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_execute_cell] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred while executing cell {cell_index}: {e}") from e

    def __del__(self):
        """Clean up any remaining kernel clients when the provider is destroyed."""
        for kernel in self._kernel_cache.values():
            try:
                kernel.stop()
            except:
                pass
        self._kernel_cache.clear()
