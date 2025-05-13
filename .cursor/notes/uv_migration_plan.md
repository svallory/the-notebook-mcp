# UV Migration Plan for the-notebook-mcp

This document outlines the steps to migrate the `the-notebook-mcp` project to use `uv` for Python environment and package management, replacing tools like `venv` and `pip` for these purposes.

## Tasks

1.  **Install `uv` (System-Wide or Verify Existence):**
    *   **Action:** Ensure `uv` is installed and accessible in the PATH.
    *   **Command (macOS/Linux):** `curl -LsSf https://astral.sh/uv/install.sh | sh` (if not already installed).
    *   **Verification:** `uv --version`.

2.  **Clean Existing Virtual Environment (Recommended):**
    *   **Action:** Remove the current `.venv` directory to ensure a fresh environment creation by `uv`.
    *   **Command:** `command rm -rf .venv` (run from project root).

3.  **Create Virtual Environment with `uv`:**
    *   **Action:** Use `uv` to create a new virtual environment.
    *   **Command:** `uv venv` (this will create a `.venv` directory by default).
    *   **Activation:** The activation command remains the same: `source .venv/bin/activate` (for macOS/Linux).

4.  **Install Project Dependencies with `uv`:**
    *   **Action:** Install the project in editable mode along with its dependencies and optional development dependencies using `uv`.
    *   **Command (for dev setup):** `uv pip install -e ".[dev]"` (this reads `pyproject.toml`).
    *   **Command (for basic install):** `uv pip install -e .`

5.  **Update `README.md` Instructions:**
    *   **Action:** Modify the "Installation" and "Development Installation (From Source)" sections in `README.md`.
    *   Replace `python -m venv .venv` with `uv venv`.
    *   Replace `pip install ...` commands with `uv pip install ...` equivalents.

6.  **Update `run_tests.sh`:**
    *   **Action:** Inspect `run_tests.sh`. If it contains explicit calls to `python -m venv`, `pip install`, or activates a venv in a specific way that is now handled differently by `uv`-managed environments, update it.
    *   Often, `uv run <command>` can simplify test execution by running the command within the `uv`-managed environment automatically.

7.  **Verify Project Functionality:**
    *   **Action (Run Server):** Test running the MCP server.
    *   **Command:** `gtimeout 5 uv run python -m the_notebook_mcp.server --allow-root /work/the-notebook-mcp` (or the user's preferred absolute path).
    *   **Action (Run Tests):** Execute the test suite.
    *   **Command:** `uv run pytest` (or `uv run ./run_tests.sh` if that script is updated and preferred).

## Post-Migration Checks:

*   Ensure all previous workflows (running server, running tests, potentially building) are functional using `uv`.
*   Confirm that `.gitignore` correctly ignores any `uv`-specific cache files if they are not placed in standard cache locations already ignored (uv aims for XDG compliance, so this is often not an issue).

### Startup with Stdio Transport

*   **Old Command:** `python /path/to/cloned/repo/cursor_notebook_mcp/server/main.py --allow-root /work/the-notebook-mcp`
*   **New Poetry Command:** `poetry run the-notebook-mcp --allow-root /work/the-notebook-mcp`
*   **New UV Command:** `uv run the-notebook-mcp --allow-root /work/the-notebook-mcp`
    *   This relies on `the-notebook-mcp` being an installed script from `pyproject.toml`.
*   **Alternative New UV Command (direct module execution):** `uv run python -m the_notebook_mcp.server --allow-root /work/the-notebook-mcp`

### Startup with SSE Transport 