"""
SSE Transport implementation for the Notebook MCP Server.

Uses Starlette and Uvicorn to serve the MCP server over SSE.
"""

import logging
import asyncio
from typing import Any

from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.responses import JSONResponse

# Use try-except for optional SSE dependencies
try:
    from mcp.server.sse import SseServerTransport
    import uvicorn
except ImportError as e:
    # Define dummy classes or raise a more informative error later if SSE is selected
    SseServerTransport = None
    uvicorn = None
    _sse_import_error = e
else:
    _sse_import_error = None

logger = logging.getLogger(__name__)

def run_sse_server(mcp_server: Any, config: Any):
    """
    Runs the MCP server using SSE transport.

    Args:
        mcp_server: The initialized FastMCP server instance.
        config: The ServerConfig object containing host, port, allowed_roots, etc.
        
    Raises:
        ImportError: If required SSE/Uvicorn packages are not installed.
        Exception: For other server startup errors.
    """
    if SseServerTransport is None or uvicorn is None:
        logger.error(f"SSE transport requires additional packages ('mcp-sdk[sse]', 'uvicorn'). Install error: {_sse_import_error}")
        raise ImportError(
            "SSE transport requires additional packages. "
            f"Please install with 'pip install \"cursor-notebook-mcp[sse]\"' or 'pip install uvicorn mcp-sdk[sse]'. Error: {_sse_import_error}"
        ) from _sse_import_error

    # Create SSE transport instance, messages are posted back to this path
    transport = SseServerTransport("/messages/")

    async def handle_sse(request):
        """Handles incoming SSE connection requests."""
        client_addr = f"{request.client.host}:{request.client.port}"
        logger.info(f"New SSE connection request from {client_addr}")
        try:
            # connect_sse handles the SSE handshake and provides streams
            async with transport.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                logger.info(f"SSE connection established with {client_addr}")
                # Run the core MCP message loop with the established streams
                await mcp_server._mcp_server.run(
                    streams[0], # Input stream
                    streams[1], # Output stream
                    mcp_server._mcp_server.create_initialization_options()
                )
                logger.info(f"SSE connection closed for {client_addr}")
        except Exception as e:
            # Log exceptions during the connection lifecycle
            logger.exception(f"Error during SSE connection with {client_addr}: {e}")
            # Re-raise to potentially send an error response if handshake hasn't completed
            raise

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