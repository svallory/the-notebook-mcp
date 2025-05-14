"""
Server entry point logic within the package.

Handles argument parsing, configuration, logging setup,
and launching the appropriate transport.
"""

import sys
import os
import inspect

from .core.config import ServerConfig # Updated import path
from .core import branding # Updated import path
from .tools import (
    CellToolsProvider,
    FileToolsProvider,
    InfoToolsProvider,
    MetadataToolsProvider,
    OutputToolsProvider,
    DiagnosticToolsProvider,
)
from .cli import parse_arguments
from .core.logging import setup_logging # Import the new setup_logging function

# --- External Dependencies ---
try:
    from fastmcp import FastMCP
    from loguru import logger
except ImportError as e:
    missing_module = str(e).split("'")[1]  # Extract the missing module name from the error message
    logger.critical(f"FATAL: Failed to import required library '{missing_module}'. Error: {e}")
    # Add hint about installing extras if it's an SSE component missing
    if "uvicorn" in str(e) or "starlette" in str(e):
        logger.error("Hint: SSE transport requires optional dependencies. Try installing with '[sse]' extra.")
    sys.exit(1)

def setup_mcp_server(config: ServerConfig) -> FastMCP:
    """Initializes the FastMCP server and registers tools from all providers.

    Args:
        config: The server configuration object.

    Returns:
        The configured FastMCP server instance.
    """
    logger.debug("Initializing FastMCP server...") # Changed to DEBUG
    mcp_server = FastMCP(
        "notebook_mcp",
        title="Jupyter Notebook MCP",
        description="Provides tools to interact with and manipulate Jupyter Notebook files.",
        version=config.version, # Pass version from config
        log_level='ERROR' # Keep FastMCP's internal logging less verbose unless debugging FastMCP itself
    )

    logger.debug("Initializing tool providers...") # Changed to DEBUG
    # Instantiate all tool providers, passing the config
    providers = [
        CellToolsProvider(config),
        FileToolsProvider(config),
        InfoToolsProvider(config),
        MetadataToolsProvider(config),
        OutputToolsProvider(config),
        DiagnosticToolsProvider(config),
    ]

    logger.debug("Registering tools with FastMCP...") # Changed to DEBUG
    registered_count = 0
    for provider_instance in providers:
        # Iterate through methods of the provider instance
        for name, method in inspect.getmembers(provider_instance, predicate=inspect.iscoroutinefunction):
            # Basic check: assume public coroutine methods starting with 'notebook_' or 'diagnose_'
            # are intended as tools. Could use a decorator later for more robustness.
            if (name.startswith("notebook_") or name.startswith("diagnose_")) and not name.startswith('_'):
                try:
                    # The mcp_server.tool() decorator registers the tool when applied
                    mcp_server.tool()(method)
                    registered_count += 1
                    # Individual registration is very verbose, TRACE might be better if needed, DEBUG summary is enough
                    # logger.trace(f"Registered tool: {provider_instance.__class__.__name__}.{name}")
                except Exception as e:
                    logger.error(f"Failed to register tool {provider_instance.__class__.__name__}.{name}: {e}", exc_info=True)

    if registered_count == 0:
        logger.warning("No tools were registered. Check provider methods and registration logic.")
    else:
        logger.debug(f"Successfully registered {registered_count} tools.") # Changed to DEBUG

    return mcp_server

def main():
    """Main entry point for the server."""
    # Initial, very basic logging setup for messages before full config.
    # This will be replaced by setup_logging later if 'start' command proceeds.
    # For 'version' command or argparse errors, this basic setup is fine.
    logger.remove() 
    logger.add(sys.stderr, level="INFO", format="{message}") # Simple format for early messages

    args = parse_arguments() # cli.py now handles 'help' (except for 'help --version')

    if args.command == 'version':
        # This handles the 'the-notebook-mcp version' subcommand
        print(f"the_notebook_mcp.server {ServerConfig().version}")
        sys.exit(0)
    elif args.command == 'help' and hasattr(args, 'help_cmd_show_version') and args.help_cmd_show_version:
        # This handles the 'the-notebook_mcp help --version' case
        print(f"the_notebook_mcp.server {ServerConfig().version}")
        sys.exit(0)

    # If we reach here, args.command must be 'start' because other commands
    # (version, help, help --version) are handled above or exit within parse_arguments().
    # Argparse 'required=True' for subcommands should enforce a valid command.
        
    # Now proceed with 'start' command logic (config setup and server launch).
    try:
        # ServerConfig will use args from the 'start' subparser.
        # The 'allow_root_dirs' in args is now guaranteed if command is 'start'.
        config = ServerConfig(args=args)

        # Setup full logging AFTER config is parsed (and only for 'start')
        setup_logging(config.log_dir, config.log_level)

    except ValueError as e: # Catch config validation errors
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.opt(exception=True).critical(f"Unexpected error during argument parsing or config initialization: {e}")
        sys.exit(1)

    # Display banner and initial config info
    # Use the get_server_startup_message from branding module
    startup_message = branding.get_server_startup_message(config)
    logger.bind(literal=True).opt(colors=True).info(startup_message)

    try:
        mcp_server = setup_mcp_server(config)

        if config.transport == "stdio":
            logger.debug("Starting server with STDIO transport.")
            mcp_server.run(**config.get_run_kwargs())
        elif config.transport == "streamable-http" or config.transport == "sse":
            logger.debug(f"Starting server with {config.transport.upper()} transport.")
            mcp_server.run(**config.get_run_kwargs())
        else:
            # This case should be caught by ServerConfig validation, but as a fallback:
            logger.critical(f"Invalid transport specified: {config.transport}. Exiting.")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Server shutting down due to KeyboardInterrupt (Ctrl+C).")
        sys.exit(0)
    except Exception as e:
        # Catch-all for any other unexpected errors during server setup or run
        logger.opt(exception=True).critical(f"Critical unexpected error in server execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # This allows running the server directly using `python -m the_notebook_mcp.server`
    main() 