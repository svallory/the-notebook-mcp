"""
Server entry point logic within the package.

Handles argument parsing, configuration, logging setup,
and launching the appropriate transport.
"""

import sys
import os
import argparse
import logging # Will be replaced by Loguru interceptor
import inspect

# --- Loguru Import ---
from loguru import logger

# --- Package-Internal Imports ---
try:
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
except ImportError as e:
    # Use Loguru for early errors if possible, otherwise print
    logger.critical(f"Error importing package components: {e}. Ensure package structure is correct.")
    sys.exit(1)

# --- External Dependencies ---
try:
    from fastmcp import FastMCP
except ImportError as e:
    # This might occur if dependencies aren't installed correctly
    logger.critical(f"FATAL: Failed to import required libraries (nbformat, etc.). Error: {e}")
    # Add hint about installing extras if it's an SSE component missing
    if "uvicorn" in str(e) or "starlette" in str(e):
        logger.error("Hint: SSE transport requires optional dependencies. Try installing with '[sse]' extra.")
    sys.exit(1)

# --- Loguru Configuration ---

class InterceptHandler(logging.Handler):
    """
    Default handler from Loguru documentation to redirect standard logging
    to Loguru.
    https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging
    """
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

def log_formatter(record):
    """Custom formatter that handles banner messages specially."""
    # Check for custom banner flag
    if record["extra"].get("literal"):
        # Just return the raw message for banners (with color tags intact)
        return '{message}'
    
    if record["level"].name == "INFO":
        return "<level>{level: <7}</level> <dim>|</dim> {message}\n"
    
    message_color = "white"
    
    if record["level"].name == "ERROR" or record["level"].name == "CRITICAL":
        message_color = "red"
        
    # For all other messages, use the standard format
    # Loguru will handle exceptions automatically after the formatter runs
    return "<level>{level: <7}</level> <dim>|</dim> <light-green>{name}:{module}:{line} ({function})</light-green> - " + f"<{message_color}>{{message}}</{message_color}>" + "\n{exception}"

def setup_logging(log_dir_path: str, log_level_str: str, in_prod_like_env: bool = False):
    """Configures Loguru handlers for console and file."""
    logger.remove() # Remove default handler

    # Console Handler with custom formatter that preserves banner colors
    logger.add(
        sys.stderr,
        level=log_level_str.upper(),
        format=log_formatter,
        colorize=True,
        backtrace=True,  # Show full exception stack traces
        diagnose=(log_level_str.upper() == "DEBUG")    # Show variable values in exceptions
    )

    # File Handler
    if log_dir_path:
        try:
            os.makedirs(log_dir_path, exist_ok=True)
            log_file_path = os.path.join(log_dir_path, "server.log")
            logger.add(
                log_file_path,
                level="DEBUG", # Always DEBUG for file log
                format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <7} | {process.id} | {thread.name: <15} | {name}:{module}:{function}:{line} | {message}",
                rotation="10 MB",
                retention="7 days",
                enqueue=True, # For asynchronous logging
                encoding='utf-8',
                backtrace=True,  # Show full exception stack traces
                diagnose=(log_level_str.upper() == "DEBUG"),    # Show variable values in exceptions
            )
            logger.debug(f"File logging enabled: {log_file_path}") # Log this after file handler is set up
        except OSError as e:
            logger.error(f"Could not create log directory or file {log_dir_path}: {e}. File logging disabled.")
    else:
        logger.warning("No log directory specified. File logging disabled.")

    # Intercept standard logging messages (e.g., from traitlets, FastMCP)
    # force=True to remove any existing handlers on the root logger
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    logger.debug(f"Logging initialized. Console level: {log_level_str.upper()}. Intercepting standard logging.")


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
        log_level='ERROR'
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


# --- Argument Parsing ---
DEFAULT_LOG_DIR = os.path.expanduser("~/.the-notebook-mcp")
DEFAULT_LOG_LEVEL_STR = "INFO"

# Helper function for case-insensitive log level
def case_insensitive_log_level(value):
    """Convert input log level to uppercase for case-insensitive comparison."""
    return value.upper()

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Jupyter Notebook MCP Server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--allow-root',
        action='append',
        required=True,
        metavar='DIR_PATH',
        help='Absolute path to a directory where notebooks are allowed. Can be used multiple times.'
    )
    parser.add_argument(
        '--log-dir',
        type=str,
        default=DEFAULT_LOG_DIR,
        metavar='PATH',
        help='Directory to store log files.'
    )
    parser.add_argument(
        '--log-level',
        type=case_insensitive_log_level,
        default=DEFAULT_LOG_LEVEL_STR,
        choices=['TRACE', 'DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set the console logging level (case-insensitive).'
    )
    parser.add_argument(
        '--max-cell-source-size',
        type=int,
        default=10 * 1024 * 1024, # 10 MiB
        metavar='BYTES',
        help='Maximum allowed size (bytes) for a cell\'s source content.'
    )
    parser.add_argument(
        '--max-cell-output-size',
        type=int,
        default=10 * 1024 * 1024, # 10 MiB
        metavar='BYTES',
        help='Maximum allowed size (bytes) for a cell\'s serialized output.'
    )
    parser.add_argument(
        '--transport',
        type=str,
        default='stdio',
        choices=['stdio', 'streamable-http', 'sse'],
        help='Transport protocol to use for server communication.'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
        metavar='IP_ADDR',
        help='Host to bind the server to (used for HTTP-based transports).'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8889,
        metavar='PORT_NUM',
        help='Port to bind the server to (used for HTTP-based transports).'
    )
    parser.add_argument(
        '--path',
        type=str,
        default='/mcp',
        metavar='URL_PATH',
        help='URL path for the MCP endpoint (used for HTTP-based transports).'
    )

    args = parser.parse_args()
    # No log_level_int needed for Loguru, it uses string names
    if os.path.exists(args.log_dir) and not os.path.isdir(args.log_dir):
         parser.error(f"--log-dir must be a directory path, not a file: {args.log_dir}")
    return args

# --- Main Execution Function (called by script entry point) ---
def main():
    """Parses arguments, sets up logging, initializes MCP, and runs the server."""
    args = None
    config = None
    # Logger is globally available from Loguru

    try:
        args = parse_arguments()
        config = ServerConfig(args) # ServerConfig now takes args directly
    except (SystemExit, ValueError) as e:
        # Loguru might not be set up yet, so print.
        print(f"ERROR: Configuration failed: {e}", file=sys.stderr)
        sys.exit(e.code if isinstance(e, SystemExit) else 1)
    except Exception as e:
        print(f"CRITICAL: Failed during argument parsing or validation: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        # Setup Loguru logging using string log level from config/args
        setup_logging(config.log_dir, config.log_level)
    except Exception as e:
        # Fallback basic print if Loguru setup fails critically
        print(f"CRITICAL: Failed during logging setup: {e}", file=sys.stderr)
        # Loguru's default handler might still work if part of setup_loguru_logging fails
        logger.exception("Failed during logging setup") # Use logger.exception with colors
        sys.exit(1)

    try:
        mcp_server = setup_mcp_server(config)
    except Exception:
        logger.exception("Failed to initialize MCP server or tools.") # Use logger.exception with colors
        sys.exit(1)
    
    try:
        # Log startup message using branding
        logger.debug(f"Starting Notebook MCP Server v{config.version}...")
        
        # Show detailed server startup banner
        startup_message = branding.get_server_startup_message(
            server_version=config.version,
            host=config.host if config.transport != "stdio" else None,
            port=config.port if config.transport != "stdio" else None,
            transport=config.transport
        )
        
        # Use bind() with literal to skip formatting
        logger.bind(literal=True).opt(colors=True).info(startup_message)
        
        # Run the server with the configured transport and options
        try:
            # Get the appropriate kwargs for the run method based on transport
            run_kwargs = config.get_run_kwargs()
            
            # Use the kwargs from config
            mcp_server.run(**run_kwargs)
            logger.debug("Server finished.")
        except ImportError as e:
            logger.exception(f"Failed to start server due to missing packages: {e}")
            if config.transport in ["streamable-http", "sse"]:
                logger.error("Hint: HTTP transports require optional dependencies. Try installing with '[http]' extra (e.g. the-notebook-mcp[http]).")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Press Enter to exit.")
    except Exception:
        print("Exception caught")
        print(sys.exc_info()[0])
        logger.exception("Server encountered a fatal error during execution.") # Use logger.exception with colors
        sys.exit(1)

if __name__ == "__main__":
    main() 