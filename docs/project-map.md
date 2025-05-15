# Project Map: the_notebook_mcp

This document provides a summary of the Python files, classes, and functions within the `the_notebook_mcp` package.

## `the_notebook_mcp/__init__.py`

*   **Summary:** Package initializer for `the_notebook_mcp`. Defines the package version and indicates that components are imported directly where needed.

## `the_notebook_mcp/mcp_setup.py`

*   **Summary:** Sets up the FastMCP server instance and dynamically registers tools from various provider classes.
*   **Functions:**
    *   `setup_mcp_server(config: ServerConfig) -> FastMCP`: Initializes the FastMCP server and registers tools from all discovered providers based on method naming conventions.

## `the_notebook_mcp/core/`

### `the_notebook_mcp/core/__init__.py`

*   **Summary:** *File does not exist.* Uses implicit namespace packaging.

### `the_notebook_mcp/core/config.py`

*   **Summary:** Defines the server configuration class, responsible for holding and validating configuration derived from command-line arguments.
*   **Classes:**
    *   `ServerConfig`: Holds server configuration like allowed roots, log settings, transport details, and size limits.
        *   `__init__(self, args: argparse.Namespace)`: Initializes the configuration from parsed command-line arguments, performing validation.

### `the_notebook_mcp/core/notebook_ops.py`

*   **Summary:** Provides core, low-level notebook file operations (read, write, path validation) designed to be independent of global state.
*   **Functions:**
    *   `is_path_allowed(target_path: str, allowed_roots: List[str]) -> bool`: Checks if a target path is safely contained within one of the configured allowed root directories.
    *   `read_notebook(notebook_path: str, allowed_roots: List[str]) -> nbformat.NotebookNode`: Reads a notebook file safely after performing security checks (absolute path, allowed root, file existence).
    *   `write_notebook(notebook_path: str, nb: nbformat.NotebookNode, allowed_roots: List[str])`: Writes a notebook object to a file safely after performing security checks and ensuring the parent directory exists.

## `the_notebook_mcp/server/`

### `the_notebook_mcp/server/main.py`

*   **Summary:** Main server entry point. Handles argument parsing, configuration loading, logging setup, MCP server initialization (via `mcp_setup`), and launching the appropriate transport (stdio or SSE). Includes a custom logging filter to suppress specific `traitlets` validation errors.
*   **Classes:**
    *   `TraitletsValidationFilter(logging.Filter)`: A custom logging filter to suppress specific `traitlets` validation error messages about unexpected 'id' properties in notebook JSON.
        *   `filter(self, record: logging.LogRecord) -> bool`: Determines if a log record should be suppressed based on the filter's criteria.
*   **Functions:**
    *   `setup_logging(log_dir: str, log_level: int)`: Configures the root logger for file and stream (stderr) output, applying the custom `TraitletsValidationFilter`.
    *   `parse_arguments() -> argparse.Namespace`: Defines and parses command-line arguments for server configuration.
    *   `main()`: The main execution function orchestrating argument parsing, config creation, logging setup, MCP server initialization, and transport running.

## `the_notebook_mcp/tools/`

### `the_notebook_mcp/tools/__init__.py`

*   **Summary:** Initializes the `tools` package and imports all tool provider classes (`CellToolsProvider`, `FileToolsProvider`, etc.) making them available for registration. Defines `__all__`.

### `the_notebook_mcp/tools/tool_utils.py`

*   **Summary:** Contains shared utility functions used by various tool providers, primarily for logging and generating notebook outlines.
*   **Functions:**
    *   `log_prefix(tool_name: str, **kwargs) -> str`: Creates a standardized log prefix string for tool execution logs, including the tool name and arguments.
    *   `extract_code_outline(source: str) -> List[str]`: Parses Python code source using `ast` to extract function and class definition names.
    *   `extract_markdown_outline(source: str) -> List[Tuple[int, str]]`: Extracts ATX-style markdown headings (e.g., `# heading`) and their levels from markdown source.
    *   `get_first_line_context(source: str, max_lines: int = 3) -> List[str]`: Retrieves the first few non-empty, non-comment lines from a source string for context.

### `the_notebook_mcp/tools/cell_tools.py`

*   **Summary:** Provides tools focused on manipulating individual cells within a notebook: adding, editing, deleting, moving, splitting, merging, changing type, and duplicating.
*   **Classes:**
    *   `CellToolsProvider`: Encapsulates cell manipulation tools.
        *   `__init__(self, config: ServerConfig)`: Initializes the provider with server configuration.
        *   `notebook_edit_cell(self, notebook_path: str, cell_index: int, source: str) -> str`: Replaces the source content of a specific cell.
        *   `notebook_add_cell(self, notebook_path: str, cell_type: str, source: str, insert_after_index: int) -> str`: Adds a new cell after a specified index.
        *   `notebook_delete_cell(self, notebook_path: str, cell_index: int) -> str`: Deletes a specific cell.
        *   `notebook_move_cell(self, notebook_path: str, from_index: int, to_index: int) -> str`: Moves a cell from one index to another.
        *   `notebook_split_cell(self, notebook_path: str, cell_index: int, split_at_line: int) -> str`: Splits a cell into two at a specific line number.
        *   `notebook_merge_cells(self, notebook_path: str, first_cell_index: int) -> str`: Merges a cell with the one immediately following it.
        *   `notebook_change_cell_type(self, notebook_path: str, cell_index: int, new_type: str) -> str`: Changes the type (code, markdown, raw) of a specific cell.
        *   `notebook_duplicate_cell(self, notebook_path: str, cell_index: int, count: int = 1) -> str`: Duplicates a specific cell one or more times.

### `the_notebook_mcp/tools/file_tools.py`

*   **Summary:** Provides tools for managing notebook files as a whole: creating, deleting, renaming, validating structure, and exporting to different formats via `nbconvert`.
*   **Classes:**
    *   `FileToolsProvider`: Encapsulates notebook file operation tools.
        *   `__init__(self, config: ServerConfig)`: Initializes the provider with server configuration.
        *   `notebook_create(self, notebook_path: str) -> str`: Creates a new, empty notebook file.
        *   `notebook_delete(self, notebook_path: str) -> str`: Deletes an existing notebook file.
        *   `notebook_rename(self, old_path: str, new_path: str) -> str`: Renames or moves a notebook file.
        *   `notebook_validate(self, notebook_path: str) -> str`: Validates a notebook file against the `nbformat` schema by attempting to read it.
        *   `notebook_export(self, notebook_path: str, export_format: str, output_path: str) -> str`: Exports a notebook to a specified format using an external `jupyter nbconvert` command.

### `the_notebook_mcp/tools/info_tools.py`

*   **Summary:** Provides tools for reading information *about* notebooks and their content, including full content, individual cells, metadata, cell counts, structural outlines, and search functionality.
*   **Classes:**
    *   `InfoToolsProvider`: Encapsulates tools for retrieving notebook information.
        *   `__init__(self, config: ServerConfig)`: Initializes the provider with server configuration.
        *   `notebook_read(self, notebook_path: str) -> dict`: Reads the entire content of a notebook file as an `nbformat` object (dictionary-like).
        *   `notebook_read_cell(self, notebook_path: str, cell_index: int) -> str`: Reads the source content of a specific cell.
        *   `notebook_get_cell_count(self, notebook_path: str) -> int`: Gets the total number of cells in a notebook.
        *   `notebook_get_info(self, notebook_path: str) -> dict`: Retrieves basic file stats (path, size, modified time) and notebook structure info (cell count, format version, metadata keys).
        *   `notebook_get_outline(self, notebook_path: str) -> List[Dict]`: Generates a structural outline based on markdown headings and code cell definitions/content.
        *   `notebook_search(self, notebook_path: str, query: str, case_sensitive: bool = False) -> List[Dict]`: Searches for a string within the source of all cells, returning match locations.

### `the_notebook_mcp/tools/metadata_tools.py`

*   **Summary:** Provides tools specifically for reading and editing metadata at both the notebook level and the individual cell level.
*   **Classes:**
    *   `MetadataToolsProvider`: Encapsulates tools for metadata manipulation.
        *   `__init__(self, config: ServerConfig)`: Initializes the provider with server configuration.
        *   `notebook_read_metadata(self, notebook_path: str) -> dict`: Reads the top-level metadata of the notebook.
        *   `notebook_edit_metadata(self, notebook_path: str, metadata_updates: dict) -> str`: Updates/adds/removes keys in the notebook's top-level metadata.
        *   `notebook_read_cell_metadata(self, notebook_path: str, cell_index: int) -> dict`: Reads the metadata of a specific cell.
        *   `notebook_edit_cell_metadata(self, notebook_path: str, cell_index: int, metadata_updates: dict) -> str`: Updates/adds/removes keys in a specific cell's metadata.

### `the_notebook_mcp/tools/output_tools.py`

*   **Summary:** Provides tools focused on managing the outputs of code cells, including reading outputs and clearing them for individual cells or the entire notebook.
*   **Classes:**
    *   `OutputToolsProvider`: Encapsulates tools for handling cell outputs.
        *   `__init__(self, config: ServerConfig)`: Initializes the provider with server configuration.
        *   `notebook_read_cell_output(self, notebook_path: str, cell_index: int) -> List[dict]`: Reads the list of output objects for a specific code cell.
        *   `notebook_clear_cell_outputs(self, notebook_path: str, cell_index: int) -> str`: Clears outputs and execution count for a specific code cell.
        *   `notebook_clear_all_outputs(self, notebook_path: str) -> str`: Clears outputs and execution counts for all code cells in the notebook. 