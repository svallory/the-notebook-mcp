# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.9.0] - 2024-05-14

### Added
- Added notebook_execute_cell tool for executing cells and retrieving outputs

### Changed
- Migrated to FastMCP 2 and restructured the project
- Improved notebook_execute_cell to preserve kernel state between calls, allowing sequential execution with shared variables
- Simplified server URL handling by using URLs as provided without modification
- Single-source version in `__version__.py` using dynamic versioning in pyproject.toml

### Fixed
- Fixed version display bug in startup banner (was showing module object instead of version string)

### Removed
- Removed diagnostic_tools.py module and diagnose_imports tool functionality
- Removed references to diagnostic tools in documentation and tests

## [0.2.3] - 2025-04-20

### Added
- CI workflow using GitHub Actions (`.github/workflows/ci.yml`) to run tests on Python 3.9 and 3.12.
- Code coverage reporting via `pytest-cov` and Coveralls integration (>70% overall, >80% for core tools).
- Additional tests for `tools.py`, `server.py`, and `notebook_ops.py` targeting error conditions, edge cases, and validation logic.
- Test script `run_tests.sh` to simplify local test execution with necessary environment variables.
- Tests for SSE transport layer (`tests/test_sse_transport.py`).

### Changed
- Improved documentation in `README.md`:
  - Added Video Walkthrough section and badges (Downloads, Issues, Coverage, MCP).
  - Clarified `stdio` vs `sse` transport configuration in `mcp.json`, recommending SSE.
  - Added troubleshooting tips for `stdio` environment issues.
  - Refined "Suggested Cursor Rules" for clarity, tone, and promoting proactive tool use.
  - Removed invalid comments from JSON examples.
  - Explicitly documented external system requirements (Pandoc, LaTeX) for PDF export.
- Updated project metadata (`classifiers`, `keywords`, `urls`) in `pyproject.toml`.
- Configured `pytest` via `pyproject.toml` to set environment variables (`JUPYTER_PLATFORM_DIRS`).
- Refactored `sse_transport.py` to separate app creation (`create_starlette_app`) for better testability.

### Fixed
- Bug in `notebook_read` size estimation loop (`NameError: name 'i' is not defined`).
- Multiple test failures related to incorrect mocking, error expectations, path handling, test setup, and imports (`StringIO`, `FastMCP`).
- Invalid escape sequence in `pyproject.toml` coverage exclusion pattern.
- Several issues in SSE transport (`sse_transport.py`) related to refactoring, including incorrect `SseServerTransport` initialization, missing `/messages` route handling, and incorrect parameters passed to the underlying `mcp.server.Server.run` method, causing connection failures.
- GitHub Actions CI workflow failure (exit code 127) by switching dependency installation from `uv` to standard `pip` to ensure `pytest` is found.
- Hanging test (`test_sse_route_connection` in `tests/test_sse_transport.py`) by refactoring to call the handler directly with a mock request instead of using `TestClient`.
- CI test failure (`test_read_large_notebook_truncated`) by enabling Git LFS (`lfs: true`) in the `actions/checkout` step to correctly download large fixture files.

## [0.2.2] - 2025-04-19

### Fixed
- Suppressed noisy `traitlets` validation errors (`Notebook JSON is invalid: Additional properties are not allowed ('id' was unexpected)`) by adding a specific logging filter in `server.py` instead of changing the global logger level. This prevents valid `ERROR` messages from `traitlets` from being hidden.

### Added
- `CHANGELOG.md` file to track project changes.
- "Suggested Cursor Rules" section to `README.md` explaining best practices for using the MCP server with Cursor's AI, formatted as a copy-pasteable markdown block.

## [0.2.1] - 2025-04-18

### Added
- Initial release of the Jupyter Notebook MCP Server.
- Core functionality for manipulating Jupyter Notebook (`.ipynb`) files via MCP tools.
- Support for both `stdio` and `sse` transport modes.
- Command-line arguments for configuration (allowed roots, logging, transport, etc.).
- Security features: `--allow-root` enforcement, path validation, cell size limits.
- MCP Tools Implemented:
  - File Operations: `notebook_create`, `notebook_delete`, `notebook_rename`
  - Notebook Read Operations: `notebook_read`, `notebook_get_cell_count`, `notebook_get_info`
  - Cell Read Operations: `notebook_read_cell`, `notebook_read_cell_output`
  - Cell Manipulation: `notebook_add_cell`, `notebook_edit_cell`, `notebook_delete_cell`, `notebook_move_cell`, `notebook_change_cell_type`, `notebook_duplicate_cell`, `notebook_split_cell`, `notebook_merge_cells`
  - Metadata Operations: `notebook_read_metadata`, `notebook_edit_metadata`, `notebook_read_cell_metadata`, `notebook_edit_cell_metadata`
  - Output Management: `notebook_clear_cell_outputs`, `notebook_clear_all_outputs`
  - Utility: `notebook_validate`, `notebook_export` (via `nbconvert`)
- Basic `README.md` with installation, usage, and integration instructions.
- `pyproject.toml` for packaging and dependency management.
- Test suite using `pytest`.