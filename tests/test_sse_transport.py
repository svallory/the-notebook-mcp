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
    """Test that connecting to /sse triggers MCP connection logic."""
    # Mock the FastMCP instance and its underlying server's run method
    mock_mcp_internal_server = mock.AsyncMock()
    mock_mcp = mock.Mock(spec=FastMCP)
    mock_mcp._mcp_server = mock.Mock()
    mock_mcp._mcp_server.run = mock_mcp_internal_server # Mock the run method

    # Mock the SseServerTransport.connect_sse context manager
    # It needs to yield mock stream objects
    mock_read_stream = mock.AsyncMock()
    mock_write_stream = mock.AsyncMock()
    mock_connect_sse_cm = mock.AsyncMock()
    mock_connect_sse_cm.__aenter__.return_value = (mock_read_stream, mock_write_stream)

    app = sse_transport.create_starlette_app(mock_mcp, dummy_server_config)
    client = TestClient(app)

    # Patch the SseServerTransport directly where it's used in handle_sse
    with mock.patch('cursor_notebook_mcp.sse_transport.SseServerTransport') as MockTransportClass:
        # Configure the instance's connect_sse method
        mock_transport_instance = MockTransportClass.return_value
        mock_transport_instance.connect_sse.return_value = mock_connect_sse_cm
        
        # Simulate connecting to the SSE endpoint
        # TestClient doesn't fully support SSE streaming tests easily,
        # but we can verify the setup calls happen.
        # We expect the connection setup to proceed, calling connect_sse and then run.
        # Making a simple GET might not be enough, POST is often used for MCP init.
        # Let's try GET and see if connect_sse is called.
        try:
            # Use stream=True to mimic connection attempt, though full SSE isn't tested
            # We expect Starlette to handle the request and call our handler
             with client.stream("GET", "/sse") as response:
                 # We don't need to consume the stream, just check mocks
                 pass 
        except Exception as e:
             # Ignore potential exceptions during stream handling in TestClient
             # as we are only checking mock calls
             print(f"Ignoring TestClient stream exception: {e}")
             pass

        # Assertions
        MockTransportClass.assert_called_once() # Was SseServerTransport instantiated?
        mock_transport_instance.connect_sse.assert_called_once() # Was connect_sse called?
        # Assert that the MCP server's run method was called via the transport
        mock_mcp_internal_server.assert_awaited_once_with(
            transport='stream', 
            read_stream=mock_read_stream, 
            write_stream=mock_write_stream
        )

# TODO: Add tests for error handling in run_sse_server

# TODO: Add tests for /sse route and error handling 