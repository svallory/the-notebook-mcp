# Refactoring Guide: the-notebook-mcp

This file outlines the main tasks for refactoring the `the-notebook-mcp` project.

## High-Level Tasks

1.  **Fix README and Project Execution:** Ensure the project can be run using the instructions in the README. Update the README with the correct commands after verifying them against the code (`server.py`, `pyproject.toml`).
2.  **Update FastMCP Usage:** Replace any legacy `mcp.server.FastMCP` imports/usage with the modern `fastmcp.FastMCP` (if necessary - verify current usage).
3.  **Migrate to UV:** Replace existing Python environment and package management tools (`venv`, `pip`, `pip-tools`, etc.) with `uv`. Create a detailed task list for this in a separate note (`uv_migration_plan.md`) and execute it.
4.  **Reorganize Project Structure:** Implement a more modular and maintainable project structure for `the_notebook_mcp/`. Document the new structure and migration steps in a separate note (`reorg_plan.md`) and execute it.

## Constraint

**After each major step/task is completed, verify that the MCP server can still be successfully run.** 