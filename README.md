# Jupyter Notebook MCP Server

This directory contains a Model Context Protocol (MCP) server designed to allow AI agents (like those in Cursor or Claude Desktop) to interact with Jupyter Notebook (`.ipynb`) files.

It uses the `nbformat` library to safely manipulate notebook structures.

## Features

Exposes the following MCP tools:

*   `notebook_edit_cell`: Replaces the source content of a specific cell.
*   `notebook_add_cell`: Adds a new code or markdown cell after a specified index.
*   `notebook_delete_cell`: Deletes a specific cell.
*   `notebook_read_cell`: Reads the source content of a specific cell.
*   `notebook_get_cell_count`: Returns the total number of cells.
*   `notebook_read_metadata`: Reads the top-level notebook metadata.
*   `notebook_edit_metadata`: Updates the top-level notebook metadata.
*   `notebook_read_cell_metadata`: Reads the metadata of a specific cell.
*   `notebook_edit_cell_metadata`: Updates the metadata of a specific cell.
*   `notebook_clear_cell_outputs`: Clears the outputs and execution count of a specific cell.
*   `notebook_clear_all_outputs`: Clears outputs and execution counts for all code cells.
*   `notebook_move_cell`: Moves a cell to a different position.
*   `notebook_validate`: Validates the notebook structure against the `nbformat` schema.
*   `notebook_get_info`: Retrieves general information (cell count, metadata, kernel, language info).

## Requirements

*   Python 3.10+
*   `mcp` (Python MCP SDK)
*   `nbformat`

## Installation

1.  Clone this repository (or ensure you are in the `mcp_server` directory).
2.  Create a virtual environment (recommended):
    ```bash
    # Using Python's venv
    python -m venv .venv
    source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`

    # Or using uv (if installed)
    # uv venv
    # source .venv/bin/activate # On Windows use `.venv\Scripts\activate`
    ```
3.  Install dependencies:
    ```bash
    # Using pip
    pip install -r requirements.txt

    # Or using uv (if installed)
    # uv sync
    ```
    *(Note: `requirements.txt` includes `mcp[cli]` which provides the `mcp` command-line tool used below.)*

## Running the Server

The server uses the `stdio` transport by default. It reads JSON-RPC messages from stdin and writes responses to stdout.

To run it directly using Python:

```bash
python notebook_server.py
```

Alternatively, since `mcp[cli]` is included in requirements, you can use the `mcp` command:

```bash
mcp run notebook_server.py
```

Typically, an MCP client (like Cursor or Claude Desktop) will launch this server as a subprocess using a configuration similar to this (example for Claude Desktop):

```json
{
  "mcpServers": {
    "notebook_tools": {
      "command": "python", // Or the full path to your python executable, or 'uv run' etc.
      "args": [
        "/absolute/path/to/mcp_server/notebook_server.py" // MUST be the absolute path
      ]
      // Add "env": { ... } if your server needs environment variables
    }
  }
}
```

**Important:** Ensure the `command` and `args` in the client configuration correctly point to your Python executable (or how you intend to run it, e.g., via `uv`) and the **absolute path** to `notebook_server.py` within this directory.

## Security

*   The server currently requires **absolute paths** for notebook files for basic safety.
*   **Crucially, it lacks robust path validation against allowed workspace roots.** In a real deployment, you MUST add validation to ensure the server only operates on files within intended directories (e.g., the user's current project workspace) to prevent security vulnerabilities.