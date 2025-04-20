"""
Tests for core notebook operations in notebook_ops.py.
"""

import pytest
import os
import nbformat
from unittest import mock
from pathlib import Path
import logging
from io import StringIO # Import StringIO from io

# Import functions to test
from cursor_notebook_mcp import notebook_ops
from cursor_notebook_mcp.server import setup_logging


@pytest.mark.asyncio
async def test_read_notebook_io_error(tmp_path):
    """Test read_notebook handles IOError from nbformat.read."""
    # Create a dummy file path within the temp directory
    dummy_path = tmp_path / "dummy_read.ipynb"
    dummy_path.touch() # Create the file so path checks pass
    allowed_roots = [str(tmp_path)]
    
    # Mock nbformat.read to raise IOError
    with mock.patch('nbformat.read', side_effect=IOError("Cannot read file")):
        with pytest.raises(IOError, match="Cannot read file"):
            # Call the async function from notebook_ops with await
            await notebook_ops.read_notebook(str(dummy_path), allowed_roots)

@pytest.mark.asyncio
async def test_read_notebook_validation_error(tmp_path):
    """Test read_notebook handles ValidationError from nbformat.read."""
    dummy_path = tmp_path / "dummy_validation.ipynb"
    dummy_path.touch()
    allowed_roots = [str(tmp_path)]
    validation_error_instance = nbformat.ValidationError("Invalid notebook format")
    
    with mock.patch('nbformat.read', side_effect=validation_error_instance):
        # Expect the function to catch ValidationError and re-raise it as IOError
        with pytest.raises(IOError, match=r"Failed to read notebook file.*?Invalid notebook format"):
            await notebook_ops.read_notebook(str(dummy_path), allowed_roots)

@pytest.mark.asyncio
async def test_write_notebook_io_error(tmp_path):
    """Test write_notebook handles IOError from nbformat.write."""
    dummy_path = tmp_path / "dummy_write.ipynb"
    # Do not create the file beforehand for write test
    allowed_roots = [str(tmp_path)]
    nb = nbformat.v4.new_notebook() # Create an empty notebook object
    
    # Mock nbformat.write to raise IOError
    with mock.patch('nbformat.write', side_effect=IOError("Cannot write file")):
        with pytest.raises(IOError, match="Cannot write file"):
            await notebook_ops.write_notebook(str(dummy_path), nb, allowed_roots)

@pytest.mark.asyncio
async def test_read_notebook_file_not_found(tmp_path):
    """Test read_notebook handles FileNotFoundError."""
    non_existent_path = tmp_path / "non_existent.ipynb"
    allowed_roots = [str(tmp_path)]
    
    # Ensure the file does not exist
    assert not non_existent_path.exists()
    
    with pytest.raises(FileNotFoundError):
        await notebook_ops.read_notebook(str(non_existent_path), allowed_roots)

@pytest.mark.asyncio
async def test_read_notebook_generic_exception(tmp_path):
    """Test read_notebook handles generic Exception from nbformat.read."""
    dummy_path = tmp_path / "dummy_generic_read.ipynb"
    dummy_path.touch()
    allowed_roots = [str(tmp_path)]
    generic_error = Exception("Some generic read error")

    with mock.patch('nbformat.read', side_effect=generic_error):
        # Expect the function to catch Exception and re-raise it as IOError
        with pytest.raises(IOError, match=r"Failed to read notebook file.*?Some generic read error"):
            await notebook_ops.read_notebook(str(dummy_path), allowed_roots)

@pytest.mark.asyncio
async def test_write_notebook_generic_exception(tmp_path):
    """Test write_notebook handles generic Exception from nbformat.write."""
    dummy_path = tmp_path / "dummy_generic_write.ipynb"
    allowed_roots = [str(tmp_path)]
    nb = nbformat.v4.new_notebook()
    generic_error = Exception("Some generic write error")

    with mock.patch('nbformat.write', side_effect=generic_error):
        with pytest.raises(IOError, match=r"Failed to write notebook file.*?Some generic write error"):
            await notebook_ops.write_notebook(str(dummy_path), nb, allowed_roots)


# --- setup_logging Tests (Synchronous) ---

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

# TODO: Add more tests here