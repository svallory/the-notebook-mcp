# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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