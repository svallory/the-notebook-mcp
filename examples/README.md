# The Notebook MCP Examples

This directory contains examples demonstrating how to use the The Notebook MCP server.

## stdio Transport (Default)

For stdio transport, Cursor manages the server process automatically. You just need to create a configuration file.

### Example Configuration: `mcp.json`

```json
{
  "mcpServers": {
    "notebook_mcp": {
      "command": "the-notebook-mcp",
      "args": [
        "--allow-root", "/absolute/path/to/your/notebooks",
        "--log-level", "INFO"
      ]
    }
  }
}
```

Place this file in:
- `~/.cursor/mcp.json` for global configuration
- `.cursor/mcp.json` in your project directory for project-specific configuration

## SSE Transport (Network-based)

For SSE transport, you need to manually run the server and configure Cursor to connect to it.

### Starting the Server

Make sure the package is installed (`pip install .[sse]`) or run from the source directory using your virtual environment's Python.

```bash
# If installed:
the-notebook-mcp --transport sse --host 127.0.0.1 --port 8080 --allow-root /path/to/notebooks

# Or running from source (ensure venv is active):
# python notebook_mcp_server.py --transport sse --host 127.0.0.1 --port 8080 --allow-root /path/to/notebooks
```

### Example Configuration: `mcp.json`

```json
{
  "mcpServers": {
    "notebook_mcp": {
      "url": "http://localhost:8080/sse"
    }
  }
}
```

Place this file in:
- `~/.cursor/mcp.json` for global configuration
- `.cursor/mcp.json` in your project directory for project-specific configuration

## Verification

When configured correctly, you should see `notebook_mcp` listed in Cursor's MCP settings page under "Available Tools".

## Environment Management

If you're using a virtual environment (recommended), you need to ensure the MCP server runs within that environment.

### For stdio Transport (Cursor-managed)

Option 1: Use the absolute path to the installed script in your virtual environment (Recommended if installed):

```json
{
  "mcpServers": {
    "notebook_mcp": {
      "command": "/absolute/path/to/venv/bin/the-notebook-mcp",
      "args": ["--allow-root", "/path/to/notebooks"]
    }
  }
}
```

Option 2: Use the absolute path to Python in your virtual environment and run the main script directly:

```json
{
  "mcpServers": {
    "notebook_mcp": {
      "command": "/absolute/path/to/venv/bin/python",
      "args": ["/absolute/path/to/project/notebook_mcp_server.py", "--allow-root", "/path/to/notebooks"]
    }
  }
}
```

Option 3: Create a wrapper script (like `launch-notebook-mcp.sh` in this directory) that activates your environment:

```json
{
  "mcpServers": {
    "notebook_mcp": {
      "command": "/absolute/path/to/launch-notebook-mcp.sh",
      "args": ["--allow-root", "/path/to/notebooks"]
    }
  }
}
```

### For SSE Transport (User-managed)

Always activate your virtual environment before launching the server:

```bash
# First activate your environment
source /path/to/venv/bin/activate

# Then launch the installed server script
the-notebook-mcp --transport sse --host 127.0.0.1 --port 8080 --allow-root /path/to/notebooks
```

When using a systemd service (like `the-notebook-mcp.service` in this directory):

```ini
# In your systemd service file:

# Option 1: Use direct path to the installed script in venv (Recommended if installed)
ExecStart=/path/to/venv/bin/the-notebook-mcp --transport sse --host 127.0.0.1 --port 8080 --allow-root /path/to/notebooks

# Option 2: Or use bash to source the environment first
# ExecStart=/bin/bash -c 'source /path/to/venv/bin/activate && the-notebook-mcp --transport sse --host 127.0.0.1 --port 8080 --allow-root /path/to/notebooks'

# Option 3: Or use direct python path and script path
# ExecStart=/path/to/venv/bin/python /path/to/project/notebook_mcp_server.py --transport sse --host 127.0.0.1 --port 8080 --allow-root /path/to/notebooks
``` 