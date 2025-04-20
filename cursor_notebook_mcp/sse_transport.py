"""
SSE Transport implementation for the Notebook MCP Server.

Uses Starlette and Uvicorn to serve the MCP server over SSE.
"""

import logging
import asyncio
from typing import Any

from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.errors import ServerErrorMiddleware

from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport

# Use try-except for optional SSE dependencies
try:
    import uvicorn
except ImportError as e:
    # Define dummy classes or raise a more informative error later if SSE is selected
    SseServerTransport = None
    uvicorn = None
    _sse_import_error = e
else:
    _sse_import_error = None

logger = logging.getLogger(__name__)

# Assuming ServerConfig type hinting
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .server import ServerConfig

# Define the SSE handler endpoint
async def handle_sse(request):
    """Handles incoming SSE connections and delegates to MCP transport."""
    mcp_server = request.app.state.mcp_server
    config = request.app.state.config
    client_host = request.client.host
    client_port = request.client.port
    log_prefix = f"[SSE {client_host}:{client_port}]"
    logger.info(f"{log_prefix} New SSE connection request from {client_host}:{client_port}")

    transport = SseServerTransport()
    try:
        logger.debug(f"{log_prefix} Setting up SSE connection")
        # connect_sse handles the SSE handshake and provides streams
        async with transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            read_stream, write_stream = streams
            logger.info(f"{log_prefix} Connection established. Running MCP session.")
            # Run the MCP server logic using the established streams
            await mcp_server._mcp_server.run(
                transport='stream', 
                read_stream=read_stream, 
                write_stream=write_stream
            )
            logger.info(f"{log_prefix} MCP session finished.")
    except Exception as e:
        # Log errors during the SSE connection or MCP run phase
        logger.error(f"{log_prefix} Error during SSE connection with {client_host}:{client_port}: {e}", exc_info=True)
        # Optionally re-raise or return an error response if possible (often too late)
        # Starlette might handle sending a 500 if the connection is still open
    finally:
        logger.info(f"{log_prefix} Closing SSE connection.")
        # Cleanup handled by context managers

# Define the root status endpoint
async def handle_root(request):
    """Simple status endpoint for the root path."""
    config = request.app.state.config
    return JSONResponse({"status": "MCP SSE Server Running", "version": config.version})

# Define exception handler
async def http_exception_handler(request, exc):
    logger.warning(f"HTTP Exception: {exc.status_code} {exc.detail} for {request.url}")
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)

async def generic_exception_handler(request, exc):
    logger.exception(f"Unhandled exception for {request.url}: {exc}")
    return PlainTextResponse("Internal Server Error", status_code=500)

exception_handlers = {
    HTTPException: http_exception_handler,
    Exception: generic_exception_handler
}

# Function to create the Starlette app (refactored)
def create_starlette_app(mcp_server: FastMCP, config: 'ServerConfig') -> Starlette:
    """Creates the Starlette application instance."""
    routes = [
        Route("/", endpoint=handle_root, methods=["GET"]),
        Route("/sse", endpoint=handle_sse) # Default methods handled by SSE transport
    ]
    middleware = [
        Middleware(ServerErrorMiddleware, handler=generic_exception_handler)
    ]
    
    app = Starlette(
        routes=routes, 
        middleware=middleware,
        exception_handlers=exception_handlers,
        debug=config.log_level <= logging.DEBUG # Enable debug mode based on log level
    )
    # Store shared instances in app state
    app.state.mcp_server = mcp_server
    app.state.config = config
    return app


# Main function to run the SSE server
def run_sse_server(mcp_server: FastMCP, config: 'ServerConfig'):
    """Configures and runs the Uvicorn server for SSE transport."""
    if SseServerTransport is None or uvicorn is None:
        logger.error(f"SSE transport requires additional packages ('mcp-sdk[sse]', 'uvicorn'). Install error: {_sse_import_error}")
        raise ImportError(
            "SSE transport requires additional packages. "
            f"Please install with 'pip install \"cursor-notebook-mcp[sse]\"' or 'pip install uvicorn mcp-sdk[sse]'. Error: {_sse_import_error}"
        ) from _sse_import_error

    try:
        # Create the Starlette app
        app = create_starlette_app(mcp_server, config)
        
        logger.info(f"Starting Uvicorn server on {config.host}:{config.port}")
        uvicorn.run(
            app, 
            host=config.host, 
            port=config.port,
            log_level=config.log_level # Pass log level to uvicorn
        )
    except ImportError:
        logger.error("Failed to import uvicorn. Please install with '[sse]' extra: pip install cursor-notebook-mcp[sse]")
        raise # Re-raise for main server loop to catch
    except Exception as e:
        logger.exception(f"Failed to start or run Uvicorn server: {e}")
        raise # Re-raise for main server loop to catch

    async def health_endpoint(request):
        """Simple health check endpoint."""
        return JSONResponse({
            "status": "ok",
            "service": "Jupyter Notebook MCP Server",
            "version": config.version,
            "transport": "sse"
        })

    async def info_endpoint(request):
        """Provides basic server information."""
        return JSONResponse({
            "name": "Jupyter Notebook MCP Server",
            "version": config.version,
            "transport": "sse",
            "allowed_roots": config.allowed_roots,
            # Add other relevant config details if needed
        })

    # Define Starlette routes
    routes = [
        Route("/sse", endpoint=handle_sse), # SSE connection endpoint
        Route("/health", endpoint=health_endpoint), # Health check
        Route("/", endpoint=info_endpoint),       # Basic info
        Mount("/messages", app=transport.handle_post_message), # Endpoint for clients to POST messages
    ]

    # Create Starlette app
    app = Starlette(routes=routes, debug=config.log_level <= logging.DEBUG)

    logger.info(f"Starting Uvicorn server on http://{config.host}:{config.port}")
    
    # Configure Uvicorn logging based on server log level
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["loggers"]["uvicorn"]["level"] = logging.getLevelName(config.log_level)
    log_config["loggers"]["uvicorn.error"]["level"] = logging.getLevelName(config.log_level)
    log_config["loggers"]["uvicorn.access"]["level"] = logging.getLevelName(config.log_level)
    # Disable access logs propagation if too noisy at DEBUG level
    log_config["loggers"]["uvicorn.access"]["propagate"] = config.log_level > logging.DEBUG 

    try:
        # Run the Uvicorn server
        uvicorn.run(
            app, 
            host=config.host, 
            port=config.port, 
            log_config=log_config
        )
    except Exception as e:
        logger.exception(f"Uvicorn server failed to run: {e}")
        raise # Re-raise the exception to be caught by the main loop 