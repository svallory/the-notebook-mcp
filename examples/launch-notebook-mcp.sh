#!/bin/bash
#
# This is a wrapper script for launching the The Notebook MCP server
# with the correct Python environment.
#
# Usage:
#   ./launch-notebook-mcp.sh --allow-root /path/to/notebooks [other options]

# -- MODIFY THIS PATH TO YOUR VIRTUAL ENVIRONMENT --
VENV_PATH="$HOME/path/to/your/venv"

# Activate the virtual environment
if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
    echo "✅ Activated virtual environment: $VENV_PATH"
else
    echo "⚠️ Warning: Virtual environment not found at $VENV_PATH"
    echo "   Using system Python instead."
fi

# Launch the server with all arguments passed to this script
# This assumes 'the-notebook-mcp' is installed in the activated venv or on the PATH
the-notebook-mcp "$@"

# Alternatively, if running directly from source (and venv is active):
# python /path/to/project/notebook_mcp_server.py "$@"