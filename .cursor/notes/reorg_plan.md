# Project Reorganization Plan for the-notebook-mcp

This document outlines the plan to reorganize the project structure of `the-notebook-mcp`, primarily focusing on the `the_notebook_mcp` package to improve modularity and maintainability.

## Current Structure of `the_notebook_mcp/`

```
the_notebook_mcp/
├── __init__.py
├── notebook_ops.py  # Low-level notebook read/write/validation logic
├── server.py        # MCP server setup, argument parsing, transport handling
├── sse_transport.py # Server-Sent Events transport logic
└── tools.py         # Large NotebookTools class with all MCP tool methods
```

## Proposed New Structure for `the_notebook_mcp/`

The main goal is to break down `tools.py` into smaller, more focused modules.

```
the_notebook_mcp/
├── __init__.py
├── core/                    # Core functionalities and utilities
│   ├── __init__.py
│   ├── config.py            # ServerConfig class (moved from server.py)
│   └── notebook_ops.py      # (As is, or potentially merged if small enough)
├── server/
│   ├── __init__.py
│   ├── main.py              # Main server entry point (current server.py content, less config)
│   └── sse_transport.py     # (As is)
├── tools/
│   ├── __init__.py          # Initializes and registers all tool groups
│   ├── base_tool_provider.py # Optional: Base class for tool groups if common logic emerges
│   ├── cell_tools.py        # Tools for cell manipulation (add, edit, delete, move, split, merge, type change, duplicate)
│   ├── file_tools.py        # Tools for notebook file operations (create, delete, rename, export, validate)
│   ├── info_tools.py        # Tools for reading info (read_notebook, read_cell, get_count, get_info, get_outline, search)
│   └── metadata_tools.py    # Tools for metadata (read/edit notebook metadata, read/edit cell metadata)
│   └── output_tools.py      # Tools for cell outputs (read_output, clear_cell_output, clear_all_outputs)
│   └── diagnostic_tools.py  # Diagnostic tools (diagnose_imports)
└── mcp_setup.py           # Initializes FastMCP server instance and NotebookTools (or new tool groups)

```

## Detailed Reorganization Tasks

1.  **Create Directory Structure:**
    *   Create `the_notebook_mcp/core/`
    *   Create `the_notebook_mcp/server/`
    *   Create `the_notebook_mcp/tools/`

2.  **Move and Refactor `ServerConfig`:**
    *   Move `ServerConfig` class from `the_notebook_mcp/server.py` to `the_notebook_mcp/core/config.py`.
    *   Update imports in the main server script.

3.  **Relocate Core and Server Files:**
    *   Move `the_notebook_mcp/notebook_ops.py` to `the_notebook_mcp/core/notebook_ops.py`.
    *   Move `the_notebook_mcp/server.py` to `the_notebook_mcp/server/main.py`.
    *   Move `the_notebook_mcp/sse_transport.py` to `the_notebook_mcp/server/sse_transport.py`.
    *   Update `__init__.py` files and relative imports accordingly.
    *   Update `pyproject.toml` script entry point: `the-notebook-mcp = "the_notebook_mcp.server.main:main"`

4.  **Refactor `tools.py` into Multiple Files:**
    *   For each new tool module in `the_notebook_mcp/tools/` (e.g., `cell_tools.py`, `file_tools.py`, etc.):
        *   Create the file.
        *   Define a new class (e.g., `CellToolsProvider`).
        *   Move the relevant methods from the original `NotebookTools` class in the old `tools.py` into this new class.
        *   Ensure each provider class takes necessary dependencies (like `config`) in its `__init__`.
        *   Update imports within these new files.

5.  **Create `the_notebook_mcp/tools/__init__.py`:**
    *   This file will be responsible for importing all individual tool provider classes.
    *   It could contain a function that takes an `FastMCP` instance and a `ServerConfig` instance, then instantiates and registers all tool providers/groups with the `FastMCP` instance.

6.  **Create `the_notebook_mcp/mcp_setup.py`:**
    *   This module will be responsible for:
        *   Creating the main `FastMCP` instance.
        *   Calling the registration logic from `the_notebook_mcp/tools/__init__.py` to add all tools.
    *   The `server/main.py` will import the `FastMCP` instance from here or call a setup function.

7.  **Update `server/main.py`:**
    *   Modify it to use the new `mcp_setup.py` to get the configured `FastMCP` instance.
    *   Ensure argument parsing and remaining server logic (transport handling) still function correctly.

8.  **Delete Old `tools.py`:**
    *   Once all methods are moved and the new structure is working, delete the original `the_notebook_mcp/tools.py`.

9.  **Resolve All Imports:**
    *   Thoroughly check and fix all `import` statements across the `the_notebook_mcp` package to reflect the new structure (e.g., `from ..core.config import ServerConfig`, `from .cell_tools import CellToolsProvider`).

10. **Verify Project Functionality:**
    *   **Run Server:** `gtimeout 5 uv run python -m the_notebook_mcp.server.main --allow-root /work/the-notebook-mcp`
    *   **Run Tests:** `uv run pytest` (hoping test discovery improves or can be fixed alongside/after reorg).

## Rationale:

*   **Modularity:** Smaller files are easier to understand, maintain, and test.
*   **Separation of Concerns:**
    *   `core/`: Basic utilities and configuration.
    *   `server/`: Transport and server execution logic.
    *   `tools/`: Grouped MCP tool implementations.
    *   `mcp_setup.py`: Central point for MCP server and tool initialization.
*   **Scalability:** Easier to add new tools or groups of tools in the future.

This plan provides a clear path. Let's proceed step-by-step. 