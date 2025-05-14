from typing import List

import nbformat
from nbformat import NotebookNode
from loguru import logger

from ..core import notebook_ops
from ..core.config import ServerConfig

class OutputToolsProvider:
    """Provides MCP tools for managing cell outputs."""
    def __init__(self, config: ServerConfig):
        self.config = config
        self.read_notebook = notebook_ops.read_notebook
        self.write_notebook = notebook_ops.write_notebook
        self.is_path_allowed = notebook_ops.is_path_allowed
        logger.debug("OutputToolsProvider initialized.")

    async def notebook_read_cell_output(self, notebook_path: str, cell_index: int) -> List[dict]:
        """Reads the output(s) of a specific code cell.

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.
            cell_index: The 0-based index of the code cell whose output to read.

        Returns:
            A list of dictionaries, where each dictionary represents an output
            (following the nbformat output structure).
            Returns an empty list if the cell is not a code cell or has no outputs.
        """
        logger.debug(f"[Tool: notebook_read_cell_output] Called. Args: path={notebook_path}, index={cell_index}")
        try:
            nb = await self.read_notebook(notebook_path, self.config.allow_root_dirs)
            if not 0 <= cell_index < len(nb.cells):
                raise IndexError(f"Cell index {cell_index} is out of bounds (0-{len(nb.cells)-1}).")

            cell = nb.cells[cell_index]
            if cell.cell_type != 'code':
                logger.warning(f"[Tool: notebook_read_cell_output] Cell {cell_index} in {notebook_path} is not a code cell (type: {cell.cell_type}), returning empty output list.")
                return []

            outputs = cell.get('outputs', [])

            # --- Output Size Check (Optional but recommended) ---
            total_output_size = 0
            for output_item in outputs:
                try:
                    # Attempt to serialize each output to estimate size
                    # This is approximate; actual disk usage might differ slightly
                    output_json = nbformat.writes(NotebookNode(output_item), version=nbformat.NO_CONVERT)
                    output_size = len(output_json.encode('utf-8'))
                    total_output_size += output_size
                except Exception as e:
                    logger.warning(f"[Tool: notebook_read_cell_output] Could not serialize output item for size check: {e}")
                    # Decide how to handle: skip? include raw? fail?
                    # Including raw for now, size check might be inaccurate.


            if total_output_size > self.config.max_cell_output_size:
                # Option 1: Raise error
                # raise ValueError(f"Total output size ({total_output_size} bytes) exceeds limit ({self.config.max_cell_output_size} bytes).")
                # Option 2: Log warning and return truncated/empty (returning full for now)
                 logger.warning(f"[Tool: notebook_read_cell_output] Total output size ({total_output_size} bytes) for cell {cell_index} in {notebook_path} exceeds limit ({self.config.max_cell_output_size} bytes), returning full output anyway.")

            logger.info(f"[Tool: notebook_read_cell_output] SUCCESS - Read {len(outputs)} output items from cell {cell_index} in {notebook_path}.", tool_success=True)
            # Return copies as plain dicts
            return [dict(o) for o in outputs]

        except (PermissionError, FileNotFoundError, IndexError, ValueError, nbformat.validator.ValidationError, IOError) as e:
            logger.error(f"[Tool: notebook_read_cell_output] FAILED - {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_read_cell_output] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred while reading cell output: {e}") from e


    async def notebook_clear_cell_outputs(self, notebook_path: str, cell_index: int) -> str:
        """Clears the output(s) and execution count of a specific code cell.

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.
            cell_index: The 0-based index of the code cell to clear.
                      If the cell is not a code cell, the operation is skipped.

        Returns:
            A success message string.
        """
        logger.debug(f"[Tool: notebook_clear_cell_outputs] Called. Args: path={notebook_path}, index={cell_index}")
        modified = False
        try:
            nb = await self.read_notebook(notebook_path, self.config.allow_root_dirs)
            if not 0 <= cell_index < len(nb.cells):
                raise IndexError(f"Cell index {cell_index} is out of bounds (0-{len(nb.cells)-1}).")

            cell = nb.cells[cell_index]
            if cell.cell_type == 'code':
                if 'outputs' in cell and cell.outputs:
                    cell.outputs = []
                    modified = True
                    logger.trace(f"[Tool: notebook_clear_cell_outputs] Cleared outputs for cell {cell_index} in {notebook_path}.")
                if 'execution_count' in cell and cell.execution_count is not None:
                    cell.execution_count = None
                    modified = True
                    logger.trace(f"[Tool: notebook_clear_cell_outputs] Cleared execution count for cell {cell_index} in {notebook_path}.")

                if not modified:
                    logger.debug(f"[Tool: notebook_clear_cell_outputs] Cell {cell_index} in {notebook_path} is a code cell but had no outputs or execution count to clear.")
                    return f"Cell {cell_index} had no outputs or execution count to clear."
            else:
                logger.warning(f"[Tool: notebook_clear_cell_outputs] Cell {cell_index} in {notebook_path} is not a code cell (type: {cell.cell_type}), skipping output clearing.")
                return f"Skipped: Cell {cell_index} is not a code cell."

            await self.write_notebook(notebook_path, nb, self.config.allow_root_dirs)
            logger.info(f"[Tool: notebook_clear_cell_outputs] SUCCESS - Cleared outputs for cell {cell_index} in {notebook_path}.", tool_success=True)
            return f"Successfully cleared outputs for cell {cell_index}."

        except (PermissionError, FileNotFoundError, IndexError, ValueError, nbformat.validator.ValidationError, IOError) as e:
            logger.error(f"[Tool: notebook_clear_cell_outputs] FAILED - {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_clear_cell_outputs] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred while clearing cell outputs: {e}") from e

    async def notebook_clear_all_outputs(self, notebook_path: str) -> str:
        """Clears all outputs and execution counts from all code cells in a notebook.

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.

        Returns:
            A success message string indicating how many cells were cleared.
        """
        logger.debug(f"[Tool: notebook_clear_all_outputs] Called. Args: path={notebook_path}")
        cleared_count = 0
        try:
            nb = await self.read_notebook(notebook_path, self.config.allow_root_dirs)
            for i, cell in enumerate(nb.cells):
                if cell.cell_type == 'code':
                    cell_modified = False
                    if 'outputs' in cell and cell.outputs:
                        cell.outputs = []
                        cell_modified = True
                    if 'execution_count' in cell and cell.execution_count is not None:
                        cell.execution_count = None
                        cell_modified = True
                    if cell_modified:
                        cleared_count += 1
                        logger.trace(f"[Tool: notebook_clear_all_outputs] Cleared outputs/exec_count for cell {i} in {notebook_path}.")

            if cleared_count > 0:
                await self.write_notebook(notebook_path, nb, self.config.allow_root_dirs)
                logger.info(f"[Tool: notebook_clear_all_outputs] SUCCESS - Cleared outputs for {cleared_count} code cells in {notebook_path}.", tool_success=True)
                return f"Successfully cleared outputs for {cleared_count} code cells."
            else:
                logger.debug(f"[Tool: notebook_clear_all_outputs] No code cells with outputs or execution counts found in {notebook_path}.")
                return "No code cell outputs or execution counts to clear."

        except (PermissionError, FileNotFoundError, ValueError, nbformat.validator.ValidationError, IOError) as e:
            logger.error(f"[Tool: notebook_clear_all_outputs] FAILED - {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_clear_all_outputs] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred while clearing all outputs: {e}") from e

# Remove original placeholder comments
# ... existing code ... 