"""
Tests for the SSE transport layer (sse_transport.py).
"""

import pytest
from unittest import mock
from starlette.testclient import TestClient
import logging # Add logging import

# Import the function and potentially classes needed
from cursor_notebook_mcp import sse_transport
from cursor_notebook_mcp.server import ServerConfig # For creating dummy config
# Need SseServerTransport for patching
from mcp.server.sse import SseServerTransport
# Need FastMCP potentially for type hinting mock
from mcp.server.fastmcp import FastMCP

# --- Test Setup ---

# Minimal dummy config for tests
@pytest.fixture
def dummy_server_config(tmp_path):
    # Minimal config needed to instantiate things
    valid_root = str(tmp_path.resolve())
    args = mock.Mock(
        allow_root=[valid_root],
        log_dir=str(tmp_path / "logs"),
        log_level_int=logging.INFO,
        max_cell_source_size=1000, max_cell_output_size=500,
        transport='sse', host='127.0.0.1', port=8080 # Ensure transport is sse
    )
    return ServerConfig(args)

# --- Tests --- 

def test_root_route(dummy_server_config):
    """Test the root GET / route returns expected status JSON."""
    # Mock the MCP server instance 
    mock_mcp = mock.Mock()
    
    # Create the app instance directly using the refactored function
    app = sse_transport.create_starlette_app(mock_mcp, dummy_server_config)
    
    client = TestClient(app)
    response = client.get("/")
    
    assert response.status_code == 200
    assert response.json() == {"status": "MCP SSE Server Running", "version": dummy_server_config.version}

@pytest.mark.asyncio
async def test_sse_route_connection(dummy_server_config):
    """Test that handle_sse calls dependencies correctly."""
    # --- Mocks Setup ---
    # Mock the underlying Server.run method
    mock_internal_run = mock.AsyncMock()
    # Mock the underlying Server.create_initialization_options method
    mock_init_options = mock.Mock(name="InitializationOptionsMock")
    mock_create_options = mock.Mock(return_value=mock_init_options)
    # Mock the underlying Server instance
    mock_underlying_server = mock.Mock()
    mock_underlying_server.run = mock_internal_run
    mock_underlying_server.create_initialization_options = mock_create_options
    # Mock the FastMCP wrapper instance
    mock_mcp_wrapper = mock.Mock(spec=FastMCP)
    mock_mcp_wrapper._mcp_server = mock_underlying_server # Link wrapper to underlying mock

    # Mock the streams that connect_sse yields
    mock_read_stream = mock.AsyncMock()
    mock_write_stream = mock.AsyncMock()
    
    # Mock the connect_sse async context manager
    mock_connect_sse_cm = mock.AsyncMock()
    mock_connect_sse_cm.__aenter__.return_value = (mock_read_stream, mock_write_stream)
    
    # Mock the SseServerTransport instance 
    mock_transport_instance = mock.Mock(spec=SseServerTransport)
    mock_transport_instance.connect_sse.return_value = mock_connect_sse_cm
    
    # --- Create Mock Request and Call Handler Directly ---
    # Mock the Starlette Request object
    mock_request = mock.AsyncMock()
    # Mock app state attached to the request
    mock_request.app = mock.Mock()
    mock_request.app.state = mock.Mock()
    mock_request.app.state.mcp_server = mock_mcp_wrapper
    mock_request.app.state.sse_transport = mock_transport_instance
    mock_request.app.state.config = dummy_server_config # Include config if needed by handler
    # Mock client info if needed for logging within handler
    mock_request.client = mock.Mock()
    mock_request.client.host = "127.0.0.1"
    mock_request.client.port = 12345
    # Mock ASGI scope/receive/send if connect_sse needs them (it does)
    mock_request.scope = {}
    mock_request.receive = mock.AsyncMock()
    mock_request._send = mock.AsyncMock() # Note: _send is often used internally

    # Call the handler directly
    await sse_transport.handle_sse(mock_request)

    # --- Assertions ---
    # Check connect_sse was called on the transport instance with ASGI args
    mock_transport_instance.connect_sse.assert_called_once_with(
        mock_request.scope, mock_request.receive, mock_request._send
    )
    
    # Check create_initialization_options was called on the underlying server
    mock_create_options.assert_called_once()
    
    # Check run was called on the underlying server with correct arguments
    mock_internal_run.assert_awaited_once_with(
        read_stream=mock_read_stream, 
        write_stream=mock_write_stream,
        initialization_options=mock_init_options
    )

# TODO: Add tests for error handling in run_sse_server

# TODO: Add tests for /sse route and error handling 