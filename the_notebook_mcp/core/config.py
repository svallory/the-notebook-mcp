"""Configuration handling for the server."""

import os
from typing import Optional, List
import argparse

from .. import __version__


class ServerConfig:
    """
    Server configuration class that validates and stores configuration parameters.

    Attributes:
        version (str): Server version string.
        allow_root_dirs (List[str]): List of allowed root directories for notebook access.
        max_cell_source_size (int): Maximum allowed size (bytes) for cell source.
        max_cell_output_size (int): Maximum allowed size (bytes) for cell output.
        log_dir (str): Directory for log files.
        log_level (str): Logging level string.
        transport (str): Transport protocol to use (stdio, streamable-http, sse).
        host (str): Host to bind to (default: 0.0.0.0), used for HTTP transports.
        port (int): Port to bind to (default: 8889), used for HTTP transports.
        path (str): URL path for MCP endpoint, used for HTTP transports.
        command (str): Command for the server.
    """

    VALID_TRANSPORTS = ["stdio", "streamable-http", "sse"]

    def __init__(self, args: Optional[argparse.Namespace] = None):
        """
        Initialize configuration from command-line arguments or defaults.

        Args:
            args: Parsed command-line arguments. If None, only defaults are set and no validation is performed.
        """

        self.command = None
        self.version = __version__.__version__
        self.allow_root_dirs = []
        self.max_cell_source_size = 10 * 1024 * 1024  # 10 MiB
        self.max_cell_output_size = 10 * 1024 * 1024  # 10 MiB
        self.log_dir = os.path.expanduser("~/.the-notebook-mcp")
        self.log_level = "INFO"
        self.transport = "stdio"
        self.host = "0.0.0.0"
        self.port = 8889
        self.path = "/mcp"

        if args:
            if hasattr(args, "command"):
                self.command = args.command
            self._apply_args(args)
            self._validate()

    def _apply_args(self, args: argparse.Namespace):
        """
        Apply parsed command-line arguments to the configuration.

        Args:
            args: Parsed command-line arguments.
        """

        if hasattr(args, "allow_root_dirs"):
            self.allow_root_dirs = args.allow_root_dirs
        elif hasattr(args, "allow_root"):
            self.allow_root_dirs = args.allow_root

        if hasattr(args, "max_cell_source_size"):
            self.max_cell_source_size = args.max_cell_source_size

        if hasattr(args, "max_cell_output_size"):
            self.max_cell_output_size = args.max_cell_output_size

        if hasattr(args, "log_dir"):
            self.log_dir = args.log_dir

        if hasattr(args, "log_level"):
            self.log_level = args.log_level

        if hasattr(args, "transport"):
            self.transport = args.transport

        if hasattr(args, "host"):
            self.host = args.host

        if hasattr(args, "port"):
            self.port = args.port

        if hasattr(args, "path"):
            self.path = args.path

    def _validate(self):
        """
        Validate configuration values.

        Raises:
            ValueError: If any configuration values are invalid.
        """

        if self.command == "start" and not self.allow_root_dirs:
            raise ValueError("At least one --allow-root must be specified for the 'start' command")

        # Validate all allow_root_dirs are absolute paths and exist
        # Only validate if allow_root_dirs is not empty (e.g. for 'start' command)
        if self.allow_root_dirs:
            for dir_path in self.allow_root_dirs:
                if not os.path.isabs(dir_path):
                    raise ValueError(f"--allow-root must be an absolute path: {dir_path}")

                if not os.path.isdir(dir_path):
                    raise ValueError(f"--allow-root directory does not exist: {dir_path}")

        if self.max_cell_source_size <= 0:
            raise ValueError(f"--max-cell-source-size must be positive: {self.max_cell_source_size}")

        if self.max_cell_output_size <= 0:
            raise ValueError(f"--max-cell-output-size must be positive: {self.max_cell_output_size}")

        if self.transport not in self.VALID_TRANSPORTS:
            raise ValueError(f"Invalid transport: {self.transport}. Must be one of {', '.join(self.VALID_TRANSPORTS)}")

        if self.transport in ["streamable-http", "sse"]:
            if not 1 <= self.port <= 65535:
                raise ValueError(f"Port must be between 1 and 65535, got {self.port}")

            if not self.path.startswith("/"):
                raise ValueError(f"Path must start with /, got '{self.path}'")

    def get_run_kwargs(self) -> dict:
        """
        Get the appropriate kwargs for FastMCP's run() method based on the configured transport.

        Returns:
            A dictionary of kwargs to pass to FastMCP.run().
        """

        kwargs = {}

        if self.transport == "stdio":
            kwargs["transport"] = "stdio"
        elif self.transport == "streamable-http":
            kwargs.update(
                {
                    "transport": "streamable-http",
                    "host": self.host,
                    "port": self.port,
                    "path": self.path,
                    "log_level": self.log_level.lower(),
                }
            )
        elif self.transport == "sse":
            kwargs.update(
                {
                    "transport": "sse",
                    "host": self.host,
                    "port": self.port,
                    "path": self.path,
                    "log_level": self.log_level.lower(),
                }
            )

        return kwargs
