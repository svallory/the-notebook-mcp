"""
Pytest configuration and fixtures for notebook MCP server tests.
"""

import pytest
import sys
from pathlib import Path
from typing import Callable
import uuid
import shutil
from the_notebook_mcp.core.config import ServerConfig

# from the_notebook_mcp.tools import NotebookTools # Commented out problematic import
from mcp.server.fastmcp import FastMCP

# Add project root to sys.path to allow importing the package
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

# Import necessary components from the package and server script

# --- Fixtures ---


@pytest.fixture(scope="session")
def temp_notebook_dir(tmp_path_factory) -> Path:
    """Create a temporary directory to act as the allowed root for notebooks."""
    temp_dir = tmp_path_factory.mktemp("notebook_tests_")
    print(f"Created temporary test directory: {temp_dir}")
    return temp_dir


@pytest.fixture(scope="function")
def server_config(temp_notebook_dir: Path) -> ServerConfig:
    """Provides a ServerConfig instance configured for testing."""

    class MockArgs:
        command = "start"
        allow_root_dirs = [str(temp_notebook_dir)]
        log_dir = str(temp_notebook_dir / "logs")
        log_level_int = 10  # DEBUG
        max_cell_source_size = 10 * 1024 * 1024
        max_cell_output_size = 10 * 1024 * 1024
        transport = "stdio"
        host = "127.0.0.1"
        port = 8080
        path = "/mcp"

    return ServerConfig(MockArgs())


@pytest.fixture(scope="function")
def mcp_server_inst() -> FastMCP:
    """Provides a clean FastMCP instance for each test function."""
    return FastMCP("test_notebook_mcp")


# @pytest.fixture(scope="function")
# def notebook_tools_inst(server_config: ServerConfig, mcp_server_inst: FastMCP) -> NotebookTools:
#     """Provides an initialized NotebookTools instance with registered tools."""
#     # Instantiating NotebookTools registers tools on mcp_server_inst
#     return NotebookTools(server_config, mcp_server_inst)


@pytest.fixture
def notebook_path_factory(temp_notebook_dir: Path) -> Callable[[], str]:
    """Provides a function to generate unique notebook paths within the test dir."""

    def _create_path() -> str:
        filename = f"test_nb_{uuid.uuid4()}.ipynb"
        return str(temp_notebook_dir / filename)

    return _create_path


# Fixture to provide an async event loop for tests marked with @pytest.mark.asyncio
# This might be automatically handled by pytest-asyncio, but defining it explicitly can sometimes help.
# Removing custom event_loop fixture as pytest-asyncio provides one automatically
# and redefining it causes a DeprecationWarning.


@pytest.fixture(scope="session")
def cli_command_path() -> str:
    """
    Returns the absolute path to the installed the-notebook-mcp script
    within the current environment's bin directory. Skips tests if not found.
    """
    python_executable = sys.executable
    venv_bin_path = Path(python_executable).parent

    script_name = "the-notebook-mcp"
    if sys.platform == "win32":
        script_name += ".exe"

    script_path = venv_bin_path / script_name

    if not script_path.exists():
        found_path = shutil.which(script_name)
        if found_path:
            script_path = Path(found_path)
        else:
            pytest.skip(f"'{script_name}' command not found in venv bin or PATH.")

    return str(script_path)
