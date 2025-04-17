import asyncio
import sys
import os
from typing import Any
import logging
# No changes needed for handlers import, FileHandler is part of logging
# import logging.handlers # Not strictly necessary for FileHandler

# Ensure mcp is importable, adjust path if necessary
try:
    import mcp.types as types
    from mcp.server.fastmcp import FastMCP
    import nbformat
except ImportError as e:
    # Use logger after it's configured
    # logging.error(f"Failed to import required libraries...") # Defer this
    print(f"FATAL: Failed to import required libraries. Make sure 'mcp-sdk' and 'nbformat' are installed. Error: {e}", file=sys.stderr)
    sys.exit(1)

# --- Logging Setup ---
LOG_DIR = os.path.expanduser("~/.mcp_server_logs")
LOG_FILE = os.path.join(LOG_DIR, "server.log")

# Create log directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

# Get root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO) # Set the minimum level for the logger

# Create Formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Create File Handler
try:
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO) # Set level for this handler
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
except Exception as e:
    # Fallback if file logging fails
    print(f"WARNING: Could not set up file logging to {LOG_FILE}. Error: {e}", file=sys.stderr)

# Create Stream Handler (to also log to stderr)
stream_handler = logging.StreamHandler(sys.stderr)
stream_handler.setLevel(logging.INFO) # Set level for this handler
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# Log initial messages now that logging is configured
logger.info(f"Logging initialized. Log file: {LOG_FILE}")
# Now log the import error if it happened (though script would have exited)
# except ImportError handling already exited, so this is conceptual

# Remove the old basicConfig
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s') # REMOVED

# Initialize FastMCP server
# The server name 'notebook_mcp' will be used by clients to identify it.
mcp = FastMCP("notebook_mcp")

# --- Helper Function for Notebook Handling ---

async def _read_notebook(notebook_path: str) -> nbformat.NotebookNode:
    """Reads a notebook file safely."""
    if not os.path.isabs(notebook_path):
        logging.error(f"Security Risk: Received non-absolute path: {notebook_path}")
        raise ValueError("Invalid notebook path: Only absolute paths are allowed.")
    # Basic check for .ipynb extension (can be made more robust)
    if not notebook_path.endswith(".ipynb"):
        raise ValueError("Invalid file type: Path must point to a .ipynb file.")
    # Check if the file exists
    if not os.path.isfile(notebook_path):
        raise FileNotFoundError(f"Notebook file not found at: {notebook_path}")
    
    # Add workspace/root validation here in a real scenario
    # Example: Check if notebook_path is within allowed roots

    try:
        return nbformat.read(notebook_path, as_version=4)
    except Exception as e:
        logging.error(f"Error reading notebook {notebook_path}: {e}")
        raise IOError(f"Failed to read notebook file: {e}") from e

async def _write_notebook(notebook_path: str, nb: nbformat.NotebookNode):
    """Writes a notebook file safely."""
    # Path validation should have happened in _read_notebook or the tool handler
    try:
        nbformat.write(nb, notebook_path)
    except Exception as e:
        logging.error(f"Error writing notebook {notebook_path}: {e}")
        raise IOError(f"Failed to write notebook file: {e}") from e

# --- Tool Definitions ---

@mcp.tool()
async def notebook_edit_cell(notebook_path: str, cell_index: int, source: str) -> str:
    """Replaces the source content of a specific cell in a Jupyter Notebook.

    Args:
        notebook_path: Absolute path to the .ipynb file.
        cell_index: The 0-based index of the cell to edit.
        source: The new source code or markdown content for the cell.
    """
    # Enhanced logging
    log_prefix = f"[Tool: notebook_edit_cell(path='{notebook_path}', index={cell_index})]"
    logging.info(f"{log_prefix} Called.")
    # logging.info(f"Attempting to edit cell {cell_index} in notebook: {notebook_path}") # Redundant now
    try:
        nb = await _read_notebook(notebook_path)
        if not 0 <= cell_index < len(nb.cells):
            raise IndexError(f"Cell index {cell_index} is out of bounds (0-{len(nb.cells)-1}).")
        
        nb.cells[cell_index].source = source
        await _write_notebook(notebook_path, nb)
        logging.info(f"{log_prefix} SUCCESS - Edited cell.")
        return f"Successfully edited cell {cell_index} in {notebook_path}"
    except (ValueError, FileNotFoundError, IndexError, IOError) as e:
        logging.error(f"{log_prefix} FAILED - Specific error: {e}")
        raise  # Re-raise to be caught by FastMCP's error handling
    except Exception as e:
        logging.exception(f"{log_prefix} FAILED - Unexpected error: {e}")
        raise RuntimeError(f"An unexpected error occurred: {e}") from e


@mcp.tool()
async def notebook_add_cell(notebook_path: str, cell_type: str, source: str, insert_after_index: int) -> str:
    """Adds a new cell to a Jupyter Notebook after the specified index.

    Args:
        notebook_path: Absolute path to the .ipynb file.
        cell_type: Type of cell ('code' or 'markdown'). Must be lowercase.
        source: The source code or markdown content for the new cell.
        insert_after_index: The 0-based index after which to insert the new cell (-1 to insert at the beginning).
    """
    # Enhanced logging
    log_prefix = f"[Tool: notebook_add_cell(path='{notebook_path}', type='{cell_type}', after_index={insert_after_index})]"
    logging.info(f"{log_prefix} Called.")
    # logging.info(f"Attempting to add {cell_type} cell after index {insert_after_index} in notebook: {notebook_path}") # Redundant now
    try:
        nb = await _read_notebook(notebook_path)
        
        if cell_type == 'code':
            new_cell = nbformat.v4.new_code_cell(source)
        elif cell_type == 'markdown':
            new_cell = nbformat.v4.new_markdown_cell(source)
        else:
            raise ValueError("Invalid cell_type: Must be 'code' or 'markdown'.")

        # Calculate the actual insertion index (insert_after_index + 1)
        insertion_index = insert_after_index + 1
        if not 0 <= insertion_index <= len(nb.cells):
             raise IndexError(f"Insertion index {insertion_index} (based on insert_after_index {insert_after_index}) is out of bounds (0-{len(nb.cells)}).")

        nb.cells.insert(insertion_index, new_cell)
        await _write_notebook(notebook_path, nb)
        logging.info(f"{log_prefix} SUCCESS - Added cell at index {insertion_index}.")
        return f"Successfully added {cell_type} cell at index {insertion_index} in {notebook_path}"
    except (ValueError, FileNotFoundError, IndexError, IOError) as e:
        logging.error(f"{log_prefix} FAILED - Specific error: {e}")
        raise
    except Exception as e:
        logging.exception(f"{log_prefix} FAILED - Unexpected error: {e}")
        raise RuntimeError(f"An unexpected error occurred: {e}") from e


@mcp.tool()
async def notebook_delete_cell(notebook_path: str, cell_index: int) -> str:
    """Deletes a specific cell from a Jupyter Notebook.

    Args:
        notebook_path: Absolute path to the .ipynb file.
        cell_index: The 0-based index of the cell to delete.
    """
    # Enhanced logging
    log_prefix = f"[Tool: notebook_delete_cell(path='{notebook_path}', index={cell_index})]"
    logging.info(f"{log_prefix} Called.")
    # logging.info(f"Attempting to delete cell {cell_index} from notebook: {notebook_path}") # Redundant now
    try:
        nb = await _read_notebook(notebook_path)
        if not 0 <= cell_index < len(nb.cells):
            raise IndexError(f"Cell index {cell_index} is out of bounds (0-{len(nb.cells)-1}).")

        del nb.cells[cell_index]
        await _write_notebook(notebook_path, nb)
        logging.info(f"{log_prefix} SUCCESS - Deleted cell.")
        return f"Successfully deleted cell {cell_index} from {notebook_path}"
    except (ValueError, FileNotFoundError, IndexError, IOError) as e:
        logging.error(f"{log_prefix} FAILED - Specific error: {e}")
        raise
    except Exception as e:
        logging.exception(f"{log_prefix} FAILED - Unexpected error: {e}")
        raise RuntimeError(f"An unexpected error occurred: {e}") from e

@mcp.tool()
async def notebook_read_cell(notebook_path: str, cell_index: int) -> str:
    """Reads the source content of a specific cell from a Jupyter Notebook.

    Args:
        notebook_path: Absolute path to the .ipynb file.
        cell_index: The 0-based index of the cell to read.
    """
    # Enhanced logging
    log_prefix = f"[Tool: notebook_read_cell(path='{notebook_path}', index={cell_index})]"
    logging.info(f"{log_prefix} Called.")
    # logging.info(f"Attempting to read cell {cell_index} from notebook: {notebook_path}") # Redundant now
    try:
        nb = await _read_notebook(notebook_path)
        if not 0 <= cell_index < len(nb.cells):
            raise IndexError(f"Cell index {cell_index} is out of bounds (0-{len(nb.cells)-1}).")

        source = nb.cells[cell_index].source
        logging.info(f"{log_prefix} SUCCESS - Read cell.")
        # Potentially truncate long cell contents if needed
        MAX_LEN = 2000 
        if len(source) > MAX_LEN:
             logging.warning(f"{log_prefix} WARNING - Content truncated.")
             return source[:MAX_LEN] + "... (truncated)"
        return source
    except (ValueError, FileNotFoundError, IndexError, IOError) as e:
        logging.error(f"{log_prefix} FAILED - Specific error: {e}")
        raise
    except Exception as e:
        logging.exception(f"{log_prefix} FAILED - Unexpected error: {e}")
        raise RuntimeError(f"An unexpected error occurred: {e}") from e

# --- NEW ADVANCED TOOLS ---

@mcp.tool()
async def notebook_get_cell_count(notebook_path: str) -> int:
    """Returns the total number of cells in the notebook."""
    log_prefix = f"[Tool: notebook_get_cell_count(path='{notebook_path}')]"
    logging.info(f"{log_prefix} Called.")
    try:
        nb = await _read_notebook(notebook_path)
        count = len(nb.cells)
        logging.info(f"{log_prefix} SUCCESS - Count: {count}")
        return count
    except (ValueError, FileNotFoundError, IOError) as e:
        logging.error(f"{log_prefix} FAILED - Specific error: {e}")
        raise
    except Exception as e:
        logging.exception(f"{log_prefix} FAILED - Unexpected error: {e}")
        raise RuntimeError(f"An unexpected error occurred: {e}") from e

@mcp.tool()
async def notebook_read_metadata(notebook_path: str) -> dict:
    """Reads the top-level metadata of the notebook."""
    log_prefix = f"[Tool: notebook_read_metadata(path='{notebook_path}')]"
    logging.info(f"{log_prefix} Called.")
    try:
        nb = await _read_notebook(notebook_path)
        metadata = dict(nb.metadata) # Convert NotebookNode metadata to dict
        logging.info(f"{log_prefix} SUCCESS - Read metadata.")
        # Consider truncating large metadata if necessary for display
        return metadata
    except (ValueError, FileNotFoundError, IOError) as e:
        logging.error(f"{log_prefix} FAILED - Specific error: {e}")
        raise
    except Exception as e:
        logging.exception(f"{log_prefix} FAILED - Unexpected error: {e}")
        raise RuntimeError(f"An unexpected error occurred: {e}") from e

@mcp.tool()
async def notebook_edit_metadata(notebook_path: str, metadata_updates: dict) -> str:
    """Updates the top-level metadata of the notebook. Merges provided updates."""
    log_prefix = f"[Tool: notebook_edit_metadata(path='{notebook_path}')]"
    logging.info(f"{log_prefix} Called with updates: {metadata_updates}")
    try:
        nb = await _read_notebook(notebook_path)
        # Update existing metadata with new values
        nb.metadata.update(metadata_updates)
        await _write_notebook(notebook_path, nb)
        logging.info(f"{log_prefix} SUCCESS - Updated metadata.")
        return f"Successfully updated metadata for {notebook_path}"
    except (ValueError, FileNotFoundError, IOError) as e:
        logging.error(f"{log_prefix} FAILED - Specific error: {e}")
        raise
    except Exception as e:
        logging.exception(f"{log_prefix} FAILED - Unexpected error: {e}")
        raise RuntimeError(f"An unexpected error occurred: {e}") from e

@mcp.tool()
async def notebook_read_cell_metadata(notebook_path: str, cell_index: int) -> dict:
    """Reads the metadata of a specific cell."""
    log_prefix = f"[Tool: notebook_read_cell_metadata(path='{notebook_path}', index={cell_index})]"
    logging.info(f"{log_prefix} Called.")
    try:
        nb = await _read_notebook(notebook_path)
        if not 0 <= cell_index < len(nb.cells):
            raise IndexError(f"Cell index {cell_index} is out of bounds (0-{len(nb.cells)-1}).")
        metadata = dict(nb.cells[cell_index].metadata) # Convert to dict
        logging.info(f"{log_prefix} SUCCESS - Read cell metadata.")
        return metadata
    except (ValueError, FileNotFoundError, IndexError, IOError) as e:
        logging.error(f"{log_prefix} FAILED - Specific error: {e}")
        raise
    except Exception as e:
        logging.exception(f"{log_prefix} FAILED - Unexpected error: {e}")
        raise RuntimeError(f"An unexpected error occurred: {e}") from e

@mcp.tool()
async def notebook_edit_cell_metadata(notebook_path: str, cell_index: int, metadata_updates: dict) -> str:
    """Updates the metadata of a specific cell. Merges provided updates."""
    log_prefix = f"[Tool: notebook_edit_cell_metadata(path='{notebook_path}', index={cell_index})]"
    logging.info(f"{log_prefix} Called with updates: {metadata_updates}")
    try:
        nb = await _read_notebook(notebook_path)
        if not 0 <= cell_index < len(nb.cells):
            raise IndexError(f"Cell index {cell_index} is out of bounds (0-{len(nb.cells)-1}).")
        # Update existing metadata with new values
        nb.cells[cell_index].metadata.update(metadata_updates)
        await _write_notebook(notebook_path, nb)
        logging.info(f"{log_prefix} SUCCESS - Updated cell metadata.")
        return f"Successfully updated metadata for cell {cell_index} in {notebook_path}"
    except (ValueError, FileNotFoundError, IndexError, IOError) as e:
        logging.error(f"{log_prefix} FAILED - Specific error: {e}")
        raise
    except Exception as e:
        logging.exception(f"{log_prefix} FAILED - Unexpected error: {e}")
        raise RuntimeError(f"An unexpected error occurred: {e}") from e

@mcp.tool()
async def notebook_clear_cell_outputs(notebook_path: str, cell_index: int) -> str:
    """Clears the output(s) of a specific cell."""
    log_prefix = f"[Tool: notebook_clear_cell_outputs(path='{notebook_path}', index={cell_index})]"
    logging.info(f"{log_prefix} Called.")
    try:
        nb = await _read_notebook(notebook_path)
        if not 0 <= cell_index < len(nb.cells):
            raise IndexError(f"Cell index {cell_index} is out of bounds (0-{len(nb.cells)-1}).")
        
        if hasattr(nb.cells[cell_index], 'outputs'):
            nb.cells[cell_index].outputs = []
        if hasattr(nb.cells[cell_index], 'execution_count'):
             nb.cells[cell_index].execution_count = None

        await _write_notebook(notebook_path, nb)
        logging.info(f"{log_prefix} SUCCESS - Cleared outputs.")
        return f"Successfully cleared outputs for cell {cell_index} in {notebook_path}"
    except (ValueError, FileNotFoundError, IndexError, IOError) as e:
        logging.error(f"{log_prefix} FAILED - Specific error: {e}")
        raise
    except Exception as e:
        logging.exception(f"{log_prefix} FAILED - Unexpected error: {e}")
        raise RuntimeError(f"An unexpected error occurred: {e}") from e

@mcp.tool()
async def notebook_clear_all_outputs(notebook_path: str) -> str:
    """Clears all outputs from all code cells in the notebook."""
    log_prefix = f"[Tool: notebook_clear_all_outputs(path='{notebook_path}')]"
    logging.info(f"{log_prefix} Called.")
    cleared_count = 0
    try:
        nb = await _read_notebook(notebook_path)
        for i, cell in enumerate(nb.cells):
            if cell.cell_type == 'code':
                if hasattr(cell, 'outputs') and cell.outputs:
                    cell.outputs = []
                    cleared_count += 1
                if hasattr(cell, 'execution_count') and cell.execution_count is not None:
                    cell.execution_count = None
                    # Only count if outputs were also cleared? Or count execution_count resets?
                    # Let's count if *any* clearing happened for the cell. If only execution_count was cleared, we'll count it.
                    # (Revisiting logic) - Let's simplify and only count if outputs were cleared.
                    # If execution_count was reset, it's implied.
        
        if cleared_count > 0: # Only write if changes were made
             await _write_notebook(notebook_path, nb)
             logging.info(f"{log_prefix} SUCCESS - Cleared outputs for {cleared_count} cells.")
             return f"Successfully cleared outputs for {cleared_count} code cells in {notebook_path}"
        else:
             logging.info(f"{log_prefix} SUCCESS - No outputs needed clearing.")
             return f"No code cell outputs found to clear in {notebook_path}"

    except (ValueError, FileNotFoundError, IOError) as e:
        logging.error(f"{log_prefix} FAILED - Specific error: {e}")
        raise
    except Exception as e:
        logging.exception(f"{log_prefix} FAILED - Unexpected error: {e}")
        raise RuntimeError(f"An unexpected error occurred: {e}") from e


@mcp.tool()
async def notebook_move_cell(notebook_path: str, from_index: int, to_index: int) -> str:
    """Moves a cell from one position to another."""
    log_prefix = f"[Tool: notebook_move_cell(path='{notebook_path}', from={from_index}, to={to_index})]"
    logging.info(f"{log_prefix} Called.")
    try:
        nb = await _read_notebook(notebook_path)
        num_cells = len(nb.cells)
        
        # Validate indices
        if not 0 <= from_index < num_cells:
            raise IndexError(f"Source index {from_index} is out of bounds (0-{num_cells-1}).")
        # Allow moving to the very end (index num_cells)
        if not 0 <= to_index <= num_cells:
            raise IndexError(f"Destination index {to_index} is out of bounds (0-{num_cells}).")
            
        if from_index == to_index:
             logging.info(f"{log_prefix} SKIPPED - Source and destination indices are the same.")
             return f"Cell at index {from_index} was not moved (source and destination are the same)."

        # Perform the move
        cell_to_move = nb.cells.pop(from_index)
        # Insert adjusts index automatically if to_index > from_index after pop
        nb.cells.insert(to_index, cell_to_move) 

        await _write_notebook(notebook_path, nb)
        logging.info(f"{log_prefix} SUCCESS - Moved cell from {from_index} to {to_index}.")
        return f"Successfully moved cell from index {from_index} to {to_index} in {notebook_path}"
    except (ValueError, FileNotFoundError, IndexError, IOError) as e:
        logging.error(f"{log_prefix} FAILED - Specific error: {e}")
        raise
    except Exception as e:
        logging.exception(f"{log_prefix} FAILED - Unexpected error: {e}")
        raise RuntimeError(f"An unexpected error occurred: {e}") from e


@mcp.tool()
async def notebook_validate(notebook_path: str) -> str:
    """Validates the notebook against the nbformat schema."""
    log_prefix = f"[Tool: notebook_validate(path='{notebook_path}')]"
    logging.info(f"{log_prefix} Called.")
    try:
        nb = await _read_notebook(notebook_path)
        nbformat.validate(nb)
        logging.info(f"{log_prefix} SUCCESS - Notebook is valid.")
        return "Notebook is valid according to the nbformat schema."
    except nbformat.ValidationError as e:
        logging.warning(f"{log_prefix} VALIDATION FAILED: {e}")
        # Return the validation error message
        return f"Notebook validation failed: {e}"
    except (ValueError, FileNotFoundError, IOError) as e:
        logging.error(f"{log_prefix} FAILED - Specific error: {e}")
        raise
    except Exception as e:
        logging.exception(f"{log_prefix} FAILED - Unexpected error: {e}")
        raise RuntimeError(f"An unexpected error occurred: {e}") from e


@mcp.tool()
async def notebook_get_info(notebook_path: str) -> dict:
    """Gets general information about the notebook (cell count, kernel, language)."""
    log_prefix = f"[Tool: notebook_get_info(path='{notebook_path}')]"
    logging.info(f"{log_prefix} Called.")
    try:
        nb = await _read_notebook(notebook_path)
        info = {
            "cell_count": len(nb.cells),
            "metadata": dict(nb.metadata), # Include all metadata for richness
            # Specific common metadata fields for convenience:
            "kernelspec": nb.metadata.get("kernelspec", None),
            "language_info": nb.metadata.get("language_info", None)
        }
        logging.info(f"{log_prefix} SUCCESS - Gathered notebook info.")
        return info
    except (ValueError, FileNotFoundError, IOError) as e:
        logging.error(f"{log_prefix} FAILED - Specific error: {e}")
        raise
    except Exception as e:
        logging.exception(f"{log_prefix} FAILED - Unexpected error: {e}")
        raise RuntimeError(f"An unexpected error occurred: {e}") from e



# --- Main Execution ---

if __name__ == "__main__":
    logging.info("Starting Jupyter Notebook MCP Server via stdio...")
    # Run the server using stdio transport
    # The MCP Python SDK handles JSON-RPC framing over stdin/stdout
    try:
        mcp.run(transport='stdio')
        logging.info("Server finished.")
    except Exception as e:
        logging.exception("Server encountered a fatal error during execution.")
        sys.exit(1) 