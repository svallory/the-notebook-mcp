import sys
import os
import logging
from loguru import logger

class InterceptHandler(logging.Handler):
    """
    Redirects standard logging messages to Loguru.

    This handler, when used with the standard Python `logging` module,
    captures log records and emits them through the Loguru logging system.
    It ensures that logs from libraries using the standard `logging`
    are processed by Loguru's configured handlers and formatters.

    It determines the appropriate Loguru level and finds the correct
    call frame to report the origin of the log message accurately.
    """
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emits a log record through Loguru.

        Args:
            record: The `logging.LogRecord` instance to process.
        """
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        # Traverse up the call stack to find the frame outside the logging module
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        
        # If frame is None (e.g., if called from C code or unusual context),
        # logger.opt might not adjust depth correctly. Default to current depth.
        # Loguru typically handles this well, so direct depth passing is usually robust.

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

def log_formatter(record: dict) -> str:
    """
    Custom Loguru formatter for console output.

    Handles special formatting for banner messages (passed as 'literal'),
    provides a concise format for INFO level, and uses distinct colors
    for ERROR/CRITICAL messages. Other levels get a detailed standard format.

    Args:
        record: The Loguru log record dictionary.

    Returns:
        The formatted log string.
    """
    # Check for custom banner flag
    if record["extra"].get("literal"):
        # Just return the raw message for banners (with color tags intact)
        return '{message}'
    
    if record["level"].name == "INFO":
        return "<level>{level: <7}</level> <dim>|</dim> {message}\n" # Removed trailing space for consistency
    
    message_color = "white" # Default message color
    
    if record["level"].name == "ERROR" or record["level"].name == "CRITICAL":
        message_color = "red"
        
    # For all other messages, use a detailed format
    # Loguru will handle exceptions automatically after the formatter runs
    return (
        "<level>{level: <7}</level> <dim>|</dim> "
        "<light-green>{name}:{module}:{line} ({function})</light-green> - "
        f"<{message_color}>{{message}}</{message_color}>\n{{exception}}"
    )

def setup_logging(log_dir_path: str, log_level_str: str, in_prod_like_env: bool = False) -> None:
    """
    Configures Loguru handlers for console and file logging.

    This function initializes the Loguru logging system by:
    1. Removing any pre-existing Loguru handlers.
    2. Adding a console handler with custom formatting (using `log_formatter`),
       colorization, backtraces, and conditional diagnostics.
    3. Adding a file handler (if `log_dir_path` is provided) with DEBUG level,
       detailed formatting, log rotation, retention, asynchronous queuing,
       and backtraces/diagnostics.
    4. Intercepting messages from the standard Python `logging` module and
       redirecting them through Loguru using `InterceptHandler`.
    
    The `in_prod_like_env` parameter is available for future use, e.g., to
    further adjust verbosity or features in production-like environments.

    Args:
        log_dir_path: Path to the directory where log files should be stored.
                      If empty or None, file logging is disabled.
        log_level_str: The logging level for the console handler (e.g., "INFO", "DEBUG").
                       Case-insensitive.
        in_prod_like_env: Flag indicating if the environment is production-like.
                          Currently unused but available for future enhancements.
    """
    logger.remove() # Remove default handler

    console_log_level = log_level_str.upper()
    is_debug_or_trace = console_log_level in ["DEBUG", "TRACE"]

    # Console Handler with custom formatter that preserves banner colors
    logger.add(
        sys.stderr,
        level=console_log_level,
        format=log_formatter,
        colorize=True,
        backtrace=True,  # Show full exception stack traces
        diagnose=is_debug_or_trace # Show variable values in exceptions for DEBUG/TRACE
    )

    # File Handler
    if log_dir_path:
        try:
            os.makedirs(log_dir_path, exist_ok=True)
            log_file_path = os.path.join(log_dir_path, "server.log")
            logger.add(
                log_file_path,
                level="DEBUG", # Always DEBUG for file log
                format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <7} | {process.id} | "
                         "{thread.name: <15} | {name}:{module}:{function}:{line} | {message}",
                rotation="10 MB",
                retention="7 days",
                enqueue=True, # For asynchronous logging
                encoding='utf-8',
                backtrace=True,  # Show full exception stack traces for file log as well
                diagnose=True,   # Always enable diagnose for DEBUG file log
            )
            # Log this message *after* the file handler is potentially set up
            # It will go to console, and to file if file logging was successful.
            logger.debug(f"File logging enabled: {log_file_path}")
        except OSError as e:
            # This error will go to the console handler.
            logger.error(f"Could not create log directory or file {log_dir_path}: {e}. File logging disabled.")
    else:
        logger.warning("No log directory specified. File logging disabled.")

    # Intercept standard logging messages (e.g., from traitlets, FastMCP)
    # force=True to remove any existing handlers on the root logger
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    logger.debug(f"Logging initialized. Console level: {console_log_level}. Intercepting standard logging.") 