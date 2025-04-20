"""
Tests for server setup, argument parsing, and configuration.
"""

import pytest
import argparse
import os
from unittest import mock
import logging
from io import StringIO # Import StringIO from io

# Import functions/classes to test from server.py
from cursor_notebook_mcp import server
from cursor_notebook_mcp.server import ServerConfig, parse_arguments, setup_logging

# Removed pytestmark = pytest.mark.asyncio as these tests are synchronous
# pytestmark = pytest.mark.asyncio

# --- Argument Parsing Tests ---

def test_parse_arguments_minimal_valid(tmp_path):
    """Test parsing with minimal required valid arguments."""
    valid_root = str(tmp_path.resolve())
    test_args = ['prog_name', '--allow-root', valid_root]
    with mock.patch('sys.argv', test_args):
        args = parse_arguments()
        assert args.allow_root == [valid_root]
        assert args.log_level == 'INFO' # Check default
        assert args.transport == 'stdio' # Check default

def test_parse_arguments_missing_allow_root():
    """Test that argparse exits if --allow-root is missing."""
    test_args = ['prog_name'] # Missing --allow-root
    with mock.patch('sys.argv', test_args):
        # Argparse calls sys.exit, which raises SystemExit
        with pytest.raises(SystemExit):
            parse_arguments()

def test_parse_arguments_invalid_log_level():
    """Test invalid choice for --log-level."""
    test_args = ['prog_name', '--allow-root', '/tmp', '--log-level', 'INVALID']
    with mock.patch('sys.argv', test_args):
        with pytest.raises(SystemExit):
            parse_arguments()

def test_parse_arguments_invalid_transport():
    """Test invalid choice for --transport."""
    test_args = ['prog_name', '--allow-root', '/tmp', '--transport', 'tcp']
    with mock.patch('sys.argv', test_args):
        with pytest.raises(SystemExit):
            parse_arguments()

def test_parse_arguments_log_dir_is_file(tmp_path):
    """Test error if --log-dir points to an existing file."""
    file_path = tmp_path / "log_file.txt"
    file_path.touch() # Create the file
    test_args = ['prog_name', '--allow-root', '/tmp', '--log-dir', str(file_path)]
    
    # Mock parser.error, which is called in this specific check
    with mock.patch('sys.argv', test_args), \
         mock.patch('argparse.ArgumentParser.error') as mock_error:
        # Configure the mock to raise SystemExit when called, like the original
        mock_error.side_effect = SystemExit 
        
        # Now, expect SystemExit to be raised when parser.error is called
        with pytest.raises(SystemExit):
             parse_arguments()
        # Verify the mock was called with the expected message
        mock_error.assert_called_once_with(f"--log-dir must be a directory path, not a file: {file_path}")

# --- ServerConfig Tests ---

def test_server_config_valid(tmp_path):
    """Test ServerConfig initialization with valid arguments."""
    valid_root = str(tmp_path.resolve())
    args = argparse.Namespace(
        allow_root=[valid_root],
        log_dir=str(tmp_path / "logs"),
        log_level='DEBUG', log_level_int=logging.DEBUG,
        max_cell_source_size=1000, max_cell_output_size=500,
        transport='stdio', host='localhost', port=8000
    )
    config = ServerConfig(args)
    assert config.allowed_roots == [valid_root]
    assert config.log_level == logging.DEBUG
    assert config.max_cell_source_size == 1000

def test_server_config_allow_root_not_absolute():
    """Test ServerConfig rejects non-absolute --allow-root."""
    args = argparse.Namespace(allow_root=["relative/path"], log_dir='/tmp', log_level_int=logging.INFO, max_cell_source_size=1, max_cell_output_size=1, transport='stdio', host='', port=0)
    with pytest.raises(ValueError, match="--allow-root path must be absolute"):
        ServerConfig(args)

def test_server_config_allow_root_not_dir(tmp_path):
    """Test ServerConfig rejects non-existent --allow-root directory."""
    non_existent_path = str(tmp_path / "non_existent_dir")
    args = argparse.Namespace(allow_root=[non_existent_path], log_dir='/tmp', log_level_int=logging.INFO, max_cell_source_size=1, max_cell_output_size=1, transport='stdio', host='', port=0)
    with pytest.raises(ValueError, match="--allow-root path must be an existing directory"):
        ServerConfig(args)

def test_server_config_invalid_size_limits(tmp_path):
    """Test ServerConfig rejects negative size limits."""
    valid_root = str(tmp_path.resolve())
    args_base = dict(
        allow_root=[valid_root], log_dir='/tmp', log_level_int=logging.INFO,
        transport='stdio', host='', port=0
    )
    
    # Test negative source size
    args_neg_source = argparse.Namespace(**args_base, max_cell_source_size=-1, max_cell_output_size=100)
    with pytest.raises(ValueError, match="--max-cell-source-size must be non-negative"):
        ServerConfig(args_neg_source)
        
    # Test negative output size
    args_neg_output = argparse.Namespace(**args_base, max_cell_source_size=100, max_cell_output_size=-1)
    with pytest.raises(ValueError, match="--max-cell-output-size must be non-negative"):
        ServerConfig(args_neg_output)

# --- setup_logging Tests ---

@mock.patch('os.makedirs', side_effect=OSError("Permission denied to create dir"))
@mock.patch('logging.FileHandler') # Mock FileHandler to prevent actual file creation
@mock.patch('sys.stderr', new_callable=StringIO) # Use imported StringIO
def test_setup_logging_makedirs_error(mock_stderr, mock_filehandler, mock_makedirs, tmp_path):
    """Test setup_logging handles OSError when creating log directory."""
    log_dir = str(tmp_path / "unwritable_logs")
    setup_logging(log_dir, logging.INFO)
    
    mock_makedirs.assert_called_once_with(log_dir, exist_ok=True)
    # Check that the error was printed to stderr
    assert "Could not create log directory" in mock_stderr.getvalue()
    assert "Permission denied to create dir" in mock_stderr.getvalue()
    # Check that FileHandler was NOT called because log_dir creation failed
    mock_filehandler.assert_not_called()

@mock.patch('os.makedirs') # Mock makedirs to succeed
@mock.patch('logging.FileHandler', side_effect=IOError("Cannot open log file for writing"))
@mock.patch('sys.stderr', new_callable=StringIO) # Use imported StringIO
def test_setup_logging_filehandler_error(mock_stderr, mock_filehandler, mock_makedirs, tmp_path):
    """Test setup_logging handles error when creating FileHandler."""
    log_dir = str(tmp_path / "logs")
    log_file_path = os.path.join(log_dir, "server.log")
    
    setup_logging(log_dir, logging.INFO)
    
    mock_makedirs.assert_called_once_with(log_dir, exist_ok=True)
    mock_filehandler.assert_called_once_with(log_file_path, encoding='utf-8')
    # Check that the warning was printed to stderr
    assert "Could not set up file logging" in mock_stderr.getvalue()
    assert "Cannot open log file for writing" in mock_stderr.getvalue()

# TODO: Add more setup_logging tests here

# TODO: Add tests here 