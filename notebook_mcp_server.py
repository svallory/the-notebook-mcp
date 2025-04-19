#!/usr/bin/env python3
"""
Main entry point for the Jupyter Notebook MCP Server.
Supports both stdio and SSE transports.
"""

import asyncio
import sys
import os
import argparse
# Remove unused imports if any left after refactor
# import subprocess 
# import importlib.util 
# from pathlib import Path
from typing import Any, List, Dict # Keep Any, List, Dict for config/type hints
import logging

# Ensure required libraries are available
try:
    import mcp.types as types
    from mcp.server.fastmcp import FastMCP
    import nbformat
except ImportError as e:
    print(f"FATAL: Failed to import required libraries. Make sure 'mcp-sdk' and 'nbformat' are installed. Error: {e}", file=sys.stderr)
    sys.exit(1)

# --- Project Structure Imports ---
# Import necessary components from our modules
from cursor_notebook_mcp.tools import NotebookTools
from cursor_notebook_mcp.sse_transport import run_sse_server
# notebook_ops is used by tools.py, not directly here

# --- Logging Setup ---
DEFAULT_LOG_DIR = os.path.expanduser("~/.cursor_notebook_mcp")
DEFAULT_LOG_LEVEL = logging.INFO

def setup_logging(log_dir: str, log_level: int):
    """Configures the root logger based on provided parameters."""
    log_file = os.path.join(log_dir, "server.log")

    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError as e:
        print(f"ERROR: Could not create log directory {log_dir}: {e}", file=sys.stderr)
        log_dir = None
        log_file = None

    logger = logging.getLogger() # Get root logger
    logger.setLevel(log_level)

    # Remove existing handlers to prevent duplicate logs on re-run
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    # Use a more detailed formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')

    # File Handler
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding='utf-8') # Specify encoding
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"WARNING: Could not set up file logging to {log_file}. Error: {e}", file=sys.stderr)
            log_file = None # Indicate failure
    else:
        # Only print info message if logging was attempted but failed
        if args and args.log_dir: # Check if log_dir was specified
             print(f"INFO: File logging disabled (could not create/access {args.log_dir}).", file=sys.stderr)
        # Otherwise, no message needed if it wasn't specified

    # Stream Handler (stderr)
    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # Use root logger for initial messages
    initial_message = f"Logging initialized. Level: {logging.getLevelName(log_level)}."
    if log_file:
        logging.info(f"{initial_message} Log file: {log_file}")
    else:
        logging.info(f"{initial_message} Logging to stderr only.")


# --- Configuration Class ---
class ServerConfig:
    """Holds server configuration derived from arguments."""
    # Make attributes more specific
    allowed_roots: List[str]
    max_cell_source_size: int
    max_cell_output_size: int
    log_dir: str
    log_level: int
    transport: str
    host: str
    port: int
    version: str = "0.2.0" # Example version, could be dynamic

    def __init__(self, args: argparse.Namespace):
        self.log_dir = args.log_dir
        self.log_level = args.log_level_int
        self.transport = args.transport
        self.host = args.host
        self.port = args.port

        # Validate and store allowed roots
        validated_roots = []
        if args.allow_root:
            for root in args.allow_root:
                if not os.path.isabs(root):
                    raise ValueError(f"--allow-root path must be absolute: {root}")
                # Ensure directory exists
                if not os.path.isdir(root):
                    raise ValueError(f"--allow-root path must be an existing directory: {root}")
                validated_roots.append(os.path.realpath(root))
        else:
            # This case is handled by argparse `required=True`
            pass 
        self.allowed_roots = validated_roots

        # Validate max cell sizes
        if args.max_cell_source_size < 0:
            raise ValueError(f"--max-cell-source-size must be non-negative: {args.max_cell_source_size}")
        self.max_cell_source_size = args.max_cell_source_size

        if args.max_cell_output_size < 0:
             raise ValueError(f"--max-cell-output-size must be non-negative: {args.max_cell_output_size}")
        self.max_cell_output_size = args.max_cell_output_size

# --- Argument Parsing ---
def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Jupyter Notebook MCP Server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter # Show defaults in help
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
        type=str,
        default=logging.getLevelName(DEFAULT_LOG_LEVEL),
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set the logging level.'
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
        choices=['stdio', 'sse'],
        help='Transport type to use.'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
        metavar='IP_ADDR',
        help='Host to bind the SSE server to (only used with --transport=sse).'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        metavar='PORT_NUM',
        help='Port to bind the SSE server to (only used with --transport=sse).'
    )

    args = parser.parse_args()

    # Convert log level string to logging constant
    args.log_level_int = getattr(logging, args.log_level.upper())

    # Validate log_dir path type before passing to setup_logging
    if os.path.exists(args.log_dir) and not os.path.isdir(args.log_dir):
         # Use parser.error for consistency in handling arg errors
         parser.error(f"--log-dir must be a directory path, not a file: {args.log_dir}")

    return args

# --- Main Execution ---
def main():
    """Parses arguments, sets up logging, initializes MCP, and runs the server."""
    args = None
    config = None
    logger = None # Define logger here for access in finally block if needed

    try:
        args = parse_arguments()
        config = ServerConfig(args)
    except (SystemExit, ValueError) as e:
        # Catch errors from argparse or ServerConfig validation
        print(f"ERROR: Configuration failed: {e}", file=sys.stderr)
        # SystemExit from argparse already includes exit code
        sys.exit(e.code if isinstance(e, SystemExit) else 1)
    except Exception as e:
        print(f"CRITICAL: Failed during argument parsing or validation: {e}", file=sys.stderr)
        sys.exit(1)

    # Setup Logging (can now safely use config)
    try:
        setup_logging(config.log_dir, config.log_level)
        # Get logger for this specific module after setup
        logger = logging.getLogger(__name__) 
    except Exception as e:
        # Catch errors during logging setup itself
        print(f"CRITICAL: Failed during logging setup: {e}", file=sys.stderr)
        # Fallback logging just in case setup failed partially
        logging.basicConfig(level=logging.ERROR)
        logging.exception("Logging setup failed critically")
        sys.exit(1)

    logger.info(f"Notebook MCP Server starting (Version: {config.version})")
    logger.info(f"Allowed Roots: {config.allowed_roots}")
    logger.info(f"Transport Mode: {config.transport}")
    if config.transport == 'sse':
        logger.info(f"SSE Endpoint: http://{config.host}:{config.port}")
    logger.debug(f"Full configuration: {config.__dict__}")

    # --- Initialize MCP Server and Tools ---
    try:
        mcp_server = FastMCP("notebook_mcp")
        
        # Instantiate the tool provider, passing config and MCP instance.
        # This automatically registers the tools via NotebookTools.__init__
        tool_provider = NotebookTools(config, mcp_server)
        
        # Tool registration happens within NotebookTools init
        # We can potentially add a method to NotebookTools to return the list if needed,
        # but for now, we'll assume registration was successful if no exceptions occurred.
        logger.info("Notebook tools initialized and registered.")
        # Remove the placeholder ping tool if it existed
        # if "ping" in mcp_server.tools:
        #     del mcp_server.tools["ping"] 

    except Exception as e:
        logger.exception("Failed to initialize MCP server or tools.")
        sys.exit(1)

    # --- Start Server based on Transport ---
    try:
        if config.transport == 'stdio':
            logger.info("Running server via stdio...")
            # FastMCP handles the stdio loop internally
            mcp_server.run(transport='stdio')
            logger.info("Server finished (stdio).")
        
        elif config.transport == 'sse':
            logger.info(f"Running server via SSE...")
            try:
                # Call the SSE runner function from the dedicated module
                run_sse_server(mcp_server, config)
            except ImportError as e:
                logger.error(f"Failed to start SSE server due to missing packages: {e}")
                # The error message from run_sse_server is usually informative enough
                # print(f"ERROR: {e}", file=sys.stderr)
                sys.exit(1)
            except Exception as e:
                logger.exception("Failed to start or run SSE server.")
                sys.exit(1)
            logger.info("Server finished (SSE).")
            
        else:
            # This case should be prevented by argparse choices
            logger.error(f"Internal Error: Invalid transport specified: {config.transport}")
            sys.exit(1)
            
    except Exception as e:
        # Catch errors during the mcp_server.run() or run_sse_server() execution
        logger.exception("Server encountered a fatal error during execution.")
        sys.exit(1)

if __name__ == "__main__":
    main() 