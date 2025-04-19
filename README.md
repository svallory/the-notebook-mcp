# Jupyter Notebook MCP Server (for Cursor)

This directory contains a Model Context Protocol (MCP) server designed to allow AI agents **within Cursor** to interact with Jupyter Notebook (`.ipynb`) files. It was created to overcome a limitation with Cursor. As of version 0.48.9, in Agent mode, the model could not edit notebooks or notebook cells in response to dialog in the AI chat pane. This provides the agent with a suite of MCP tools that allow direct notebook cell manipulation.

I'm sure at some point this will be handled natively by Cursor, but I have a data science background, and I live in Jupyter notebooks. I got tired of copy/paste-ing output of the chat manually into the notebook cells.

Although designed to overcome a limitation with Cursor, this MCP server does not have anything specific to Cursor other than the configuration instructions. You could easily configure this for use with Claude Code or any model/agent that can take advantage of MCP.

This MCP server uses the `nbformat` library to safely manipulate notebook structures and enforces security by restricting operations to user-defined directories. It also uses `nbconvert` to enable exporting notebooks to various formats like Python scripts, HTML, and more. The server handles all notebook operations through a clean API that maintains notebook integrity and prevents malformed changes.

## Features

Exposes the following MCP tools (registered under the `notebook_mcp` server):

*   `notebook_create`: Creates a new, empty notebook file.
*   `notebook_delete`: Deletes an existing notebook file.
*   `notebook_rename`: Renames/moves a notebook file from one path to another.
*   `notebook_read`: Reads an entire notebook and returns its structure as a dictionary.
*   `notebook_read_cell`: Reads the source content of a specific cell.
*   `notebook_add_cell`: Adds a new code or markdown cell after a specified index.
*   `notebook_edit_cell`: Replaces the source content of a specific cell.
*   `notebook_delete_cell`: Deletes a specific cell.
*   `notebook_change_cell_type`: Changes a cell's type (code, markdown, or raw).
*   `notebook_duplicate_cell`: Duplicates a cell multiple times (default: once).
*   `notebook_get_cell_count`: Returns the total number of cells.
*   `notebook_read_metadata`: Reads the top-level notebook metadata.
*   `notebook_edit_metadata`: Updates the top-level notebook metadata.
*   `notebook_read_cell_metadata`: Reads the metadata of a specific cell.
*   `notebook_read_cell_output`: Reads the output list of a specific code cell.
*   `notebook_edit_cell_metadata`: Updates the metadata of a specific cell.
*   `notebook_clear_cell_outputs`: Clears the outputs and execution count of a specific cell.
*   `notebook_clear_all_outputs`: Clears outputs and execution counts for all code cells.
*   `notebook_move_cell`: Moves a cell to a different position.
*   `notebook_split_cell`: Splits a cell into two at a specified line number.
*   `notebook_merge_cells`: Merges a cell with the cell immediately following it.
*   `notebook_validate`: Validates the notebook structure against the `nbformat` schema.
*   `notebook_get_info`: Retrieves general information (cell count, metadata, kernel, language info).
*   `notebook_export`: Exports the notebook to another format (e.g., python, html) using nbconvert.

## Requirements

*   Python 3.9+
*   **Core:** `mcp`, `nbformat>=5.0`, `nbconvert>=6.0`, `ipython`, `jupyter_core` (Installed automatically via `pip install .`)
*   **SSE Transport:** `uvicorn`, `starlette` (Installed via `pip install .[sse]`)
*   **Testing:** `pytest`, `pytest-asyncio` (Installed via `pip install .[test]`)

## Installation

### From PyPI (If Published)

```bash
# Basic installation (stdio transport only)
pip install cursor-notebook-mcp

# With SSE transport support
pip install "cursor-notebook-mcp[sse]"
```

### Development Installation (From Source)

1.  Clone this repository:
    ```bash
    git clone https://github.com/jbeno/cursor-notebook-mcp.git # Or your fork
    cd cursor-notebook-mcp
    ```

2.  Create and activate a virtual environment (recommended):
    ```bash
    # Using Python's venv
    python -m venv .venv
    source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`

    # Or using uv (if installed)
    # uv venv
    # source .venv/bin/activate # On Windows use `.venv\Scripts\activate`
    ```

3.  Install in editable mode with all optional dependencies:
    ```bash
    # Includes SSE and Test dependencies
    pip install -e ".[dev]"
    
    # Or install just the base + SSE
    # pip install -e ".[sse]"
    
    # Or install just the base
    # pip install -e .
    ```

## Running the Server

There are two main ways to run the server:

### 1. Direct Execution (Recommended for Testing/Development)

Activate your virtual environment and run the main script directly:

```bash
# stdio transport (default)
python notebook_mcp_server.py --allow-root /path/to/notebooks

# sse transport
python notebook_mcp_server.py --transport sse --allow-root /path/to/notebooks --host 127.0.0.1 --port 8080
```

### 2. Using the Installed Script (After `pip install`)

If you have installed the package (even with `-e`), the `cursor-notebook-mcp` command should be available in your virtual environment:

```bash
# stdio transport
cursor-notebook-mcp --allow-root /path/to/notebooks

# sse transport
cursor-notebook-mcp --transport sse --allow-root /path/to/notebooks --host 127.0.0.1 --port 8080
```

## Cursor Integration (`mcp.json`)

To make Cursor aware of this server, configure it in `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project-specific).

### For stdio Transport

Cursor launches and manages the server. Use the installed script path or direct python execution:

```json
{
  "mcpServers": {
    "notebook_mcp": { // Use the correct server name
      // Option 1: Use installed script (ensure venv path is correct)
      "command": "/absolute/path/to/venv/bin/cursor-notebook-mcp", 
      // Option 2: Use python and script path
      // "command": "/absolute/path/to/venv/bin/python", 
      // "args": ["/absolute/path/to/project/notebook_mcp_server.py", ... ],
      "args": [
        "--allow-root", "/absolute/path/to/your/notebooks",
        // Optional logging arguments:
        // "--log-dir", "/path/to/your/desired/log/directory",
        // "--log-level", "DEBUG"
      ],
      "env": { 
        // Add environment variables if needed
      }
    }
  }
}
```

### For SSE Transport

Run the server manually first (see "Running the Server" above), then tell Cursor where to connect:

```json
{
  "mcpServers": {
    "notebook_mcp": { // Use the correct server name
      "url": "http://localhost:8080/sse",
      "env": { 
        // Add environment variables if needed
      }
    }
  }
}
```

**Note**: When using SSE transport, make sure the server is started *before* attempting to use it in Cursor.

## Command-Line Arguments

The server accepts the following command-line arguments:

*   `--allow-root`: (Required, can use multiple times) Absolute path to directory where notebooks are allowed.
*   `--log-dir`: Directory to store log files. Defaults to `~/.cursor_notebook_mcp`.
*   `--log-level`: Set the logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. Defaults to `INFO`.
*   `--max-cell-source-size`: Maximum allowed size in bytes for cell source content. Defaults to 10 MiB.
*   `--max-cell-output-size`: Maximum allowed size in bytes for cell output content. Defaults to 10 MiB.
*   `--transport`: Transport type to use: `stdio` or `sse`. Defaults to `stdio`.
*   `--host`: Host to bind the SSE server to. Only used with `--transport=sse`. Defaults to `127.0.0.1`.
*   `--port`: Port to bind the SSE server to. Only used with `--transport=sse`. Defaults to `8080`.

## Security

*   **Workspace Root Enforcement:** The server **requires** the `--allow-root` command-line argument during startup. It will refuse to operate on any notebook file located outside the directories specified by these arguments. This is a critical security boundary.
*   **Path Handling:** The server uses `os.path.realpath` to resolve paths and checks against the allowed roots before any read or write operation.
*   **Input Validation:** Basic checks for `.ipynb` extension are performed.
*   **Cell Source Size Limit:** The server enforces a maximum size limit (configurable via `--max-cell-source-size`, default 10 MiB) on the source content provided to `notebook_edit_cell` and `notebook_add_cell` to prevent excessive memory usage.
*   **Cell Output Size Limit:** The server enforces a maximum size limit (configurable via `--max-cell-output-size`, default 10 MiB) on the total serialized size of outputs returned by `notebook_read_cell_output`.

## Limitations

*   **No Cell Execution:** This server **cannot execute** notebook cells. It operates solely on the `.ipynb` file structure using the `nbformat` library and does not interact with Jupyter kernels. Cell execution must be performed manually by the user within the Cursor UI (selecting the desired kernel and running the cell). Implementing execution capabilities in this server would require kernel management and introduce significant complexity and security considerations.

## Known Issues

*   **UI Refresh Issues:** Occasionally, some notebook operations (like cell splitting or merging) may succeed at the file level, but the Cursor UI might not show the updated content correctly. In such situations, you can:
    * Close and re-open the notebook file
    * Save the file, which might prompt to "Revert" or "Overwrite" - select "Revert" to reload the actual file content

## Development & Testing

1. Setup virtual environment and install dev dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```
2. Run tests:
   ```bash
   pytest tests/
   ```

## Issues

If you encounter any bugs or issues, please submit them to our GitHub issue tracker:

1. Visit [jbeno/cursor-notebook-mcp](https://github.com/jbeno/cursor-notebook-mcp/issues)
2. Click on "New Issue"
3. Provide:
   - A clear description of the problem
   - Steps to reproduce the issue
   - Expected vs actual behavior
   - Your environment details (OS, Python version, etc.)
   - Any relevant error messages or logs
   - Which model and client/version you're using

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a new branch for your feature (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests to ensure nothing is broken (`pytest tests/`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to your branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

Please make sure your PR:
- Includes tests for new functionality
- Updates documentation as needed
- Follows the existing code style
- Includes a clear description of the changes

For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.


## Author

This project was created and is maintained by Jim Beno - jim@jimbeno.net