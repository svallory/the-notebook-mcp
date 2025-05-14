"""
Tools for cell manipulation (add, edit, delete, move, split, merge, type change, duplicate).
"""

import copy # Needed for duplicate_cell
from loguru import logger # Import Loguru

import nbformat

# Import necessary components
from ..core.config import ServerConfig
from ..core import notebook_ops # Import the module directly

class CellToolsProvider:
    # Update __init__ signature and body
    def __init__(self, config: ServerConfig):
        self.config = config
        # Core ops functions are used directly via notebook_ops.<func_name>
        # mcp_instance is not needed here, registration happens in mcp_setup
        logger.debug("CellToolsProvider initialized.")

    # Update method calls to use imported functions
    async def notebook_edit_cell(self, notebook_path: str, cell_index: int, source: str) -> str:
        """Replaces the source content of a specific cell in a Jupyter Notebook.

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.
            cell_index: The 0-based index of the cell to edit.
            source: The new source code or markdown content for the cell.
        """
        logger.debug(f"[Tool: notebook_edit_cell] Called. Args: path={notebook_path}, index={cell_index}, source_len={len(source)}")
        try:
            # Validate source size
            if len(source.encode('utf-8')) > self.config.max_cell_source_size:
                raise ValueError(f"Source content exceeds maximum allowed size ({self.config.max_cell_source_size} bytes).")

            # Use imported notebook_ops functions
            nb = await notebook_ops.read_notebook(notebook_path, self.config.allow_root_dirs)
            if not 0 <= cell_index < len(nb.cells):
                raise IndexError(f"Cell index {cell_index} is out of bounds (0-{len(nb.cells)-1}).")
            
            nb.cells[cell_index].source = source
            await notebook_ops.write_notebook(notebook_path, nb, self.config.allow_root_dirs)
            logger.info(f"[Tool: notebook_edit_cell] SUCCESS - Edited cell {cell_index}.", tool_success=True)
            return f"Successfully edited cell {cell_index} in {notebook_path}"
        except (ValueError, FileNotFoundError, IndexError, IOError, PermissionError, nbformat.validator.ValidationError) as e:
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
        logger.debug(f"[Tool: notebook_add_cell] Called. Args: path={notebook_path}, type={cell_type}, after_index={insert_after_index}, source_len={len(source)}")
        try:
            # Validate source size
            if len(source.encode('utf-8')) > self.config.max_cell_source_size:
                raise ValueError(f"Source content exceeds maximum allowed size ({self.config.max_cell_source_size} bytes).")

            nb = await notebook_ops.read_notebook(notebook_path, self.config.allow_root_dirs)
            
            if cell_type == 'code':
                new_cell = nbformat.v4.new_code_cell(source)
            elif cell_type == 'markdown':
                new_cell = nbformat.v4.new_markdown_cell(source)
            else:
                raise ValueError("Invalid cell_type: Must be 'code' or 'markdown'.")

            insertion_index = insert_after_index + 1
            if not 0 <= insertion_index <= len(nb.cells):
                 raise IndexError(f"Insertion index {insertion_index} (based on insert_after_index {insert_after_index}) is out of bounds (0-{len(nb.cells)}).")

            nb.cells.insert(insertion_index, new_cell)
            await notebook_ops.write_notebook(notebook_path, nb, self.config.allow_root_dirs)
            logger.info(f"[Tool: notebook_add_cell] SUCCESS - Added {cell_type} cell at index {insertion_index}.", tool_success=True)
            return f"Successfully added {cell_type} cell at index {insertion_index} in {notebook_path}"
        except (ValueError, FileNotFoundError, IndexError, IOError, PermissionError, nbformat.validator.ValidationError) as e:
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
                raise IndexError(f"Cell index {cell_index} is out of bounds (0-{len(nb.cells)-1}).")

            del nb.cells[cell_index]
            await notebook_ops.write_notebook(notebook_path, nb, self.config.allow_root_dirs)
            logger.info(f"[Tool: notebook_delete_cell] SUCCESS - Deleted cell {cell_index}.", tool_success=True)
            return f"Successfully deleted cell {cell_index} from {notebook_path}"
        except (ValueError, FileNotFoundError, IndexError, IOError, PermissionError, nbformat.validator.ValidationError) as e:
            logger.error(f"[Tool: notebook_delete_cell] FAILED - Specific error: {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_delete_cell] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred: {e}") from e

    async def notebook_move_cell(self, notebook_path: str, from_index: int, to_index: int) -> str:
        """Moves a cell from one position to another."""
        logger.debug(f"[Tool: notebook_move_cell] Called. Args: path={notebook_path}, from={from_index}, to={to_index}")
        try:
            nb = await notebook_ops.read_notebook(notebook_path, self.config.allow_root_dirs)
            num_cells = len(nb.cells)
            
            if not 0 <= from_index < num_cells:
                raise IndexError(f"Source index {from_index} is out of bounds (0-{num_cells-1}).")
            # Allow moving to the very end (index == num_cells)
            if not 0 <= to_index <= num_cells: 
                raise IndexError(f"Destination index {to_index} is out of bounds (0-{num_cells}).")
                
            # No change if indices are the same or adjacent in a way that results in no move
            if from_index == to_index or from_index + 1 == to_index:
                 logger.debug("[Tool: notebook_move_cell] SKIPPED - Cell move results in no change.")
                 return f"Cell at index {from_index} was not moved (source and destination are effectively the same)."

            cell_to_move = nb.cells.pop(from_index)
            
            # Insert at the target index. If destination was after source, 
            # the list is shorter now, so insert happens at correct perceived position.
            nb.cells.insert(to_index if from_index > to_index else to_index - 1, cell_to_move)

            await notebook_ops.write_notebook(notebook_path, nb, self.config.allow_root_dirs)
            logger.info(f"[Tool: notebook_move_cell] SUCCESS - Moved cell from {from_index} to {to_index}.", tool_success=True)
            return f"Successfully moved cell from index {from_index} to {to_index} in {notebook_path}"
        except (ValueError, FileNotFoundError, IndexError, IOError, PermissionError, nbformat.validator.ValidationError) as e:
            logger.error(f"[Tool: notebook_move_cell] FAILED - Specific error: {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_move_cell] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred: {e}") from e

    # --- Other methods (split, merge, change_type, duplicate) need similar updates --- 
    # Replace self.read_notebook -> notebook_ops.read_notebook
    # Replace self.write_notebook -> notebook_ops.write_notebook
    # Replace self.create_log_prefix -> log_prefix
    # Make sure nbformat.validator.ValidationError is caught in relevant handlers

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
        logger.debug(f"[Tool: notebook_split_cell] Called. Args: path={notebook_path}, index={cell_index}, line={split_at_line}")
        try:
            nb = await notebook_ops.read_notebook(notebook_path, self.config.allow_root_dirs)
            if not 0 <= cell_index < len(nb.cells):
                raise IndexError(f"Cell index {cell_index} is out of bounds (0-{len(nb.cells)-1}).")

            cell_to_split = nb.cells[cell_index]
            source = cell_to_split.get('source', '')
            lines = source.splitlines(True) # Keep line endings

            # Convert 1-based line number to 0-based index for slicing
            split_index = split_at_line - 1

            if not 0 < split_index < len(lines):
                 raise ValueError(f"Split line number {split_at_line} is out of bounds for cell with {len(lines)} lines.")

            source_part1 = "".join(lines[:split_index])
            source_part2 = "".join(lines[split_index:])

            # --- Validate source sizes for the new cells --- 
            max_size = self.config.max_cell_source_size
            if len(source_part1.encode('utf-8')) > max_size or \
               len(source_part2.encode('utf-8')) > max_size:
                raise ValueError(f"Resulting source content after split exceeds maximum allowed size ({max_size} bytes) for one or both cells.")

            # Modify original cell
            cell_to_split.source = source_part1
            if cell_to_split.cell_type == 'code':
                cell_to_split.outputs = []
                cell_to_split.execution_count = None

            # Create new cell
            new_cell_metadata = copy.deepcopy(cell_to_split.metadata)
            if cell_to_split.cell_type == 'code':
                new_cell = nbformat.v4.new_code_cell(source=source_part2, metadata=new_cell_metadata)
            elif cell_to_split.cell_type == 'markdown':
                new_cell = nbformat.v4.new_markdown_cell(source=source_part2, metadata=new_cell_metadata)
            else: # Raw cell
                new_cell = nbformat.v4.new_raw_cell(source=source_part2, metadata=new_cell_metadata)

            # Insert new cell
            nb.cells.insert(cell_index + 1, new_cell)

            await notebook_ops.write_notebook(notebook_path, nb, self.config.allow_root_dirs)
            logger.info(f"[Tool: notebook_split_cell] SUCCESS - Split cell {cell_index} at line {split_at_line}.", tool_success=True)
            return f"Successfully split cell {cell_index} at line {split_at_line}."

        except (PermissionError, FileNotFoundError, IndexError, ValueError, nbformat.validator.ValidationError, IOError) as e:
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
            if cell1.cell_type not in ('code', 'markdown'):
                raise ValueError(f"Merging is only supported for code and markdown cells (found {cell1.cell_type}).")

            source1 = cell1.get('source', '')
            source2 = cell2.get('source', '')

            separator = "\n" 
            merged_source = source1 + separator + source2

            if len(merged_source.encode('utf-8')) > self.config.max_cell_source_size:
                raise ValueError(f"Merged source content exceeds maximum allowed size ({self.config.max_cell_source_size} bytes).")

            cell1.source = merged_source
            if cell1.cell_type == 'code':
                cell1.outputs = []
                cell1.execution_count = None

            del nb.cells[first_cell_index + 1]

            await notebook_ops.write_notebook(notebook_path, nb, self.config.allow_root_dirs)
            logger.info(f"[Tool: notebook_merge_cells] SUCCESS - Merged cell {first_cell_index + 1} into cell {first_cell_index}.", tool_success=True)
            return f"Successfully merged cell {first_cell_index + 1} into cell {first_cell_index}."

        except (PermissionError, FileNotFoundError, IndexError, ValueError, nbformat.validator.ValidationError, IOError) as e:
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
        logger.debug(f"[Tool: notebook_change_cell_type] Called. Args: path={notebook_path}, index={cell_index}, type={new_type}")

        allowed_types = ('code', 'markdown', 'raw')
        if new_type not in allowed_types:
            raise ValueError(f"Invalid target cell type '{new_type}'. Must be one of {allowed_types}.")

        try:
            nb = await notebook_ops.read_notebook(notebook_path, self.config.allow_root_dirs)
            if not 0 <= cell_index < len(nb.cells):
                raise IndexError(f"Cell index {cell_index} is out of bounds (0-{len(nb.cells)-1}).")

            original_cell = nb.cells[cell_index]
            original_type = original_cell.cell_type

            if original_type == new_type:
                logger.debug(f"[Tool: notebook_change_cell_type] Cell is already of type '{new_type}'. No change needed.")
                return f"Cell {cell_index} is already of type '{new_type}'."

            source = original_cell.get('source', '')
            metadata = copy.deepcopy(original_cell.metadata)
            attachments = copy.deepcopy(original_cell.get('attachments', {}))

            if new_type == 'code':
                new_cell = nbformat.v4.new_code_cell(source=source, metadata=metadata)
                if attachments:
                     logger.warning(f"[Tool: notebook_change_cell_type] Discarding attachments when converting cell {cell_index} to code type.")
            elif new_type == 'markdown':
                new_cell = nbformat.v4.new_markdown_cell(source=source, metadata=metadata, attachments=attachments)
            else: # new_type == 'raw'
                new_cell = nbformat.v4.new_raw_cell(source=source, metadata=metadata)
                if attachments:
                    new_cell['attachments'] = attachments

            nb.cells[cell_index] = new_cell

            await notebook_ops.write_notebook(notebook_path, nb, self.config.allow_root_dirs)
            logger.info(f"[Tool: notebook_change_cell_type] SUCCESS - Changed cell {cell_index} from '{original_type}' to '{new_type}'.", tool_success=True)
            return f"Successfully changed cell {cell_index} to type '{new_type}'."

        except (PermissionError, FileNotFoundError, IndexError, ValueError, nbformat.validator.ValidationError, IOError) as e:
            logger.error(f"[Tool: notebook_change_cell_type] FAILED - {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_change_cell_type] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred while changing cell type: {e}") from e

    async def notebook_duplicate_cell(self, notebook_path: str, cell_index: int, count: int = 1) -> str:
        """Duplicates a specific cell multiple times, inserting the copies after the original.

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.
            cell_index: The 0-based index of the cell to duplicate.
            count: The number of duplicates to create (default: 1).

        Returns:
            A success message string indicating how many duplicates were created.
        """
        logger.debug(f"[Tool: notebook_duplicate_cell] Called. Args: path={notebook_path}, index={cell_index}, count={count}")

        if count < 1:
            raise ValueError("Duplicate count must be at least 1.")

        try:
            nb = await notebook_ops.read_notebook(notebook_path, self.config.allow_root_dirs)
            if not 0 <= cell_index < len(nb.cells):
                raise IndexError(f"Cell index {cell_index} is out of bounds (0-{len(nb.cells)-1}).")

            original_cell = nb.cells[cell_index]
            duplicates = [copy.deepcopy(original_cell) for _ in range(count)]

            for dup_cell in duplicates:
                 if dup_cell.cell_type == 'code':
                     dup_cell.outputs = []
                     dup_cell.execution_count = None
                 if 'id' in dup_cell:
                      del dup_cell['id'] 

            for i, duplicate_cell in enumerate(duplicates):
                 nb.cells.insert(cell_index + 1 + i, duplicate_cell)

            await notebook_ops.write_notebook(notebook_path, nb, self.config.allow_root_dirs)
            plural = "s" if count > 1 else ""
            logger.info(f"[Tool: notebook_duplicate_cell] SUCCESS - Created {count} duplicate{plural} of cell {cell_index}.", tool_success=True)
            return f"Successfully created {count} duplicate{plural} of cell {cell_index}."

        except (PermissionError, FileNotFoundError, IndexError, ValueError, nbformat.validator.ValidationError, IOError) as e:
            logger.error(f"[Tool: notebook_duplicate_cell] FAILED - {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_duplicate_cell] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred while duplicating cell: {e}") from e 