import argparse
import os
import sys

from .core.config import ServerConfig

DEFAULT_LOG_DIR = os.path.expanduser("~/.the-notebook-mcp")
DEFAULT_LOG_LEVEL_STR = "INFO"


# Helper function for case-insensitive log level
def case_insensitive_log_level(value: str) -> str:
    """Convert input log level to uppercase for case-insensitive comparison."""
    return value.upper()


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments for the Jupyter Notebook MCP Server.

    This function sets up the argument parser with subcommands (start, version, help),
    defines all available arguments, and handles special cases like the help command.

    For the 'start' command, it defines arguments for allowed root directories,
    logging configuration, cell size limits, and network transport settings.

    Returns:
        An argparse.Namespace object containing the parsed command-line arguments.
        If no command is provided or help is requested, the function may exit the process
        after printing appropriate help text.
    """
    parser = argparse.ArgumentParser(
        description="Jupyter Notebook MCP Server.",
        # Allow showing help on error for the main parser
        # add_help=False # If we want very custom error + help
    )

    _version_str = ServerConfig().version
    parser.version = f"%(prog)s {_version_str}"

    parser.add_argument(
        "-v",
        "--version",
        action="version",  # This top-level version flag prints and exits
        help="Show program's version number and exit.",
    )

    subparsers = parser.add_subparsers(
        title="Commands",
        dest="command",
        help="Run 'python -m the_notebook_mcp.server <command> --help' for more information on a command.",
    )

    # --- Start command ---
    start_parser = subparsers.add_parser(
        "start",
        help="Start the Jupyter Notebook MCP server.",
        description="Run the Jupyter Notebook MCP server with the specified configurations.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    start_parser.add_argument(
        "--allow-root",
        dest="allow_root_dirs",
        action="append",
        required=True,
        metavar="DIR_PATH",
        help="Absolute path to a directory where notebooks are allowed. Can be used multiple times. This is required.",
    )
    start_parser.add_argument(
        "--log-dir",
        type=str,
        default=DEFAULT_LOG_DIR,
        metavar="PATH",
        help="Directory to store log files.",
    )
    start_parser.add_argument(
        "--log-level",
        type=case_insensitive_log_level,
        default=DEFAULT_LOG_LEVEL_STR,
        choices=["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"],
        help="Set the console logging level (case-insensitive).",
    )
    start_parser.add_argument(
        "--max-cell-source-size",
        type=int,
        default=10 * 1024 * 1024,  # 10 MiB
        metavar="BYTES",
        help="Maximum allowed size (bytes) for a cell's source content.",
    )
    start_parser.add_argument(
        "--max-cell-output-size",
        type=int,
        default=10 * 1024 * 1024,  # 10 MiB
        metavar="BYTES",
        help="Maximum allowed size (bytes) for a cell's serialized output.",
    )
    start_parser.add_argument(
        "--transport",
        type=str,
        default="stdio",
        choices=["stdio", "streamable-http", "sse"],
        help="Transport protocol to use for server communication.",
    )
    start_parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        metavar="IP_ADDR",
        help="Host to bind the server to (used for HTTP-based transports).",
    )
    start_parser.add_argument(
        "--port",
        type=int,
        default=8889,
        metavar="PORT_NUM",
        help="Port to bind the server to (used for HTTP-based transports).",
    )
    start_parser.add_argument(
        "--path",
        type=str,
        default="/mcp",
        metavar="URL_PATH",
        help="URL path for the MCP endpoint (used for HTTP-based transports).",
    )
    start_parser.set_defaults(command="start")

    # --- Version command ---
    version_parser = subparsers.add_parser(  # This is the 'version' subcommand
        "version", help="Show program's version number and exit."
    )
    version_parser.set_defaults(command="version")

    # --- Help command ---
    help_parser = subparsers.add_parser(
        "help",
        help="Show help for commands or program version.",
        description="Provides help information for other commands, or shows the program version.",
    )
    help_parser.add_argument(
        "cmd_to_help",
        nargs="?",  # Optional argument
        metavar="COMMAND_NAME",
        default=None,  # Default if not provided
        help="Optional command name to show help for (e.g., start, version, help).",
    )
    help_parser.add_argument(
        "--version",
        dest="help_cmd_show_version",  # Specific dest to avoid conflict
        action="store_true",
        help="Show program's version number and exit (when used with the 'help' command).",
    )
    help_parser.set_defaults(command="help")

    # --- Argument parsing and help subcommand logic ---

    # The 'choices' attribute of the subparsers action object holds the map of command names to their parsers.
    subparser_choices_map = subparsers.choices

    parsed_args = parser.parse_args()

    # Handle the case where no subcommand is provided
    if parsed_args.command is None:
        parser.print_help()
        sys.exit(0)

    if parsed_args.command == "help":
        if hasattr(parsed_args, "help_cmd_show_version") and parsed_args.help_cmd_show_version:
            # Fall through: server.py will handle printing the version for 'help --version'
            return parsed_args
        elif parsed_args.cmd_to_help:
            if parsed_args.cmd_to_help in subparser_choices_map:
                subparser_choices_map[parsed_args.cmd_to_help].print_help()
            else:
                print(
                    f"Error: Unknown command '{parsed_args.cmd_to_help}' for help.\\n",
                    file=sys.stderr,
                )
                parser.print_help(sys.stderr)
                sys.exit(1)
            sys.exit(0)
        else:
            # 'the-notebook-mcp help' (no specific command, no --version flag)
            parser.print_help()
            sys.exit(0)

    return parsed_args
