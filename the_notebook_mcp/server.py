"""
Server entry point logic within the package.

Handles argument parsing, configuration, logging setup,
and launching the appropriate transport.
"""

import sys
import inspect

from .core.config import ServerConfig
from .core import branding
from .tools import (
    CellToolsProvider,
    FileToolsProvider,
    InfoToolsProvider,
    MetadataToolsProvider,
    OutputToolsProvider,
)
from .cli import parse_arguments
from .core.logging import setup_logging

# --- External Dependencies ---
try:
    from fastmcp import FastMCP
    from loguru import logger
except ImportError as e:
    missing_module = str(e).split("'")[1]
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
    logger.debug("Initializing FastMCP server...")
    mcp_server = FastMCP(
        "notebook_mcp",
        title="Jupyter Notebook MCP",
        description="Provides tools to interact with and manipulate Jupyter Notebook files.",
        version=config.version,
        log_level="ERROR",  # Keep FastMCP's internal logging less verbose unless debugging FastMCP itself
    )

    logger.debug("Initializing tool providers...")

    providers = [
        CellToolsProvider(config),
        FileToolsProvider(config),
        InfoToolsProvider(config),
        MetadataToolsProvider(config),
        OutputToolsProvider(config),
    ]

    logger.debug("Registering tools with FastMCP...")
    registered_count = 0
    for provider_instance in providers:
        for name, method in inspect.getmembers(provider_instance, predicate=inspect.iscoroutinefunction):
            # Basic check: assume public coroutine methods starting with 'notebook_' or 'diagnose_'
            # are intended as tools. Could use a decorator later for more robustness.
            if (name.startswith("notebook_")) and not name.startswith("_"):
                try:
                    mcp_server.add_tool(method)
                    registered_count += 1

                except Exception as e:
                    logger.error(
                        f"Failed to register tool {provider_instance.__class__.__name__}.{name}: {e}",
                        exc_info=True,
                    )

    if registered_count == 0:
        logger.warning("No tools were registered. Check provider methods and registration logic.")
    else:
        logger.debug(f"Successfully registered {registered_count} tools.")

    return mcp_server


def main():
    """Main entry point for the server."""

    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{message}")

    args = parse_arguments()

    if args.command == "version":
        print(f"the_notebook_mcp.server {ServerConfig().version}")
        sys.exit(0)
    elif args.command == "help" and hasattr(args, "help_cmd_show_version") and args.help_cmd_show_version:
        print(f"the_notebook_mcp.server {ServerConfig().version}")
        sys.exit(0)

    try:
        config = ServerConfig(args=args)

        setup_logging(config.log_dir, config.log_level)

    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.opt(exception=True).critical(f"Unexpected error during argument parsing or config initialization: {e}")
        sys.exit(1)

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
            logger.critical(f"Invalid transport specified: {config.transport}. Exiting.")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Server shutting down due to KeyboardInterrupt (Ctrl+C).")
        sys.exit(0)
    except Exception as e:
        logger.opt(exception=True).critical(f"Critical unexpected error in server execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
