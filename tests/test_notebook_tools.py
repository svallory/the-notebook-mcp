"""
Integration tests for NotebookTools methods.

These tests interact with an instance of NotebookTools directly,
using shared fixtures from conftest.py for configuration and setup.
"""

import pytest
import os
import nbformat
from pathlib import Path
import importlib
import json
import asyncio
from unittest import mock
import subprocess
import sys
import builtins # Import builtins for mocking import

# Import the class to be tested
from cursor_notebook_mcp.tools import NotebookTools

# Use pytest-asyncio for async tests
pytestmark = pytest.mark.asyncio

async def test_notebook_create_delete(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test creating and then deleting a notebook."""
    nb_path = notebook_path_factory()
    
    # Ensure file does not exist initially
    assert not os.path.exists(nb_path)
    
    # Create the notebook
    create_result = await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    assert os.path.exists(nb_path)
    assert "Successfully created" in create_result
    
    # Verify it's a valid empty notebook
    nb = nbformat.read(nb_path, as_version=4)
    assert isinstance(nb, nbformat.NotebookNode)
    assert len(nb.cells) == 0
    
    # Delete the notebook
    delete_result = await notebook_tools_inst.notebook_delete(notebook_path=nb_path)
    assert not os.path.exists(nb_path)
    assert "Successfully deleted" in delete_result

async def test_notebook_create_duplicate(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test that creating a notebook with an existing path fails."""
    nb_path = notebook_path_factory()
    
    # Create the notebook once
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    assert os.path.exists(nb_path)
    
    # Attempt to create it again
    with pytest.raises(FileExistsError):
        await notebook_tools_inst.notebook_create(notebook_path=nb_path)

async def test_notebook_delete_nonexistent(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test that deleting a non-existent notebook fails correctly."""
    nb_path = notebook_path_factory()
    assert not os.path.exists(nb_path)
    
    with pytest.raises(FileNotFoundError):
        await notebook_tools_inst.notebook_delete(notebook_path=nb_path)

async def test_notebook_rename(notebook_tools_inst: NotebookTools, notebook_path_factory, temp_notebook_dir):
    """Test renaming a notebook."""
    old_path = notebook_path_factory()
    new_filename = f"renamed_nb_{Path(old_path).stem}.ipynb"
    new_path = str(temp_notebook_dir / new_filename)
    
    # Create original notebook
    await notebook_tools_inst.notebook_create(notebook_path=old_path)
    assert os.path.exists(old_path)
    assert not os.path.exists(new_path)
    
    # Rename
    rename_result = await notebook_tools_inst.notebook_rename(old_path=old_path, new_path=new_path)
    assert "Successfully renamed" in rename_result
    
    # Verify old path is gone, new path exists
    assert not os.path.exists(old_path)
    assert os.path.exists(new_path)

async def test_notebook_rename_target_exists(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test renaming fails if the target path already exists."""
    path1 = notebook_path_factory()
    path2 = notebook_path_factory()
    
    # Create both notebooks
    await notebook_tools_inst.notebook_create(notebook_path=path1)
    await notebook_tools_inst.notebook_create(notebook_path=path2)
    
    # Attempt to rename path1 to path2 (which exists)
    with pytest.raises(FileExistsError):
        await notebook_tools_inst.notebook_rename(old_path=path1, new_path=path2)

async def test_path_validation_non_absolute(notebook_tools_inst: NotebookTools):
    """Test that non-absolute paths are rejected."""
    relative_path = "relative_notebook.ipynb"
    with pytest.raises(ValueError, match="Only absolute paths are allowed"):
        await notebook_tools_inst.notebook_create(notebook_path=relative_path)
    with pytest.raises(ValueError, match="Only absolute paths are allowed"):
        await notebook_tools_inst.notebook_delete(notebook_path=relative_path)
    with pytest.raises(ValueError, match="Only absolute paths are allowed"):
        await notebook_tools_inst.notebook_rename(old_path="old.ipynb", new_path="new.ipynb")

async def test_path_validation_outside_root(notebook_tools_inst: NotebookTools, tmp_path):
    """Test that paths outside the allowed root are rejected."""
    # tmp_path is another pytest fixture providing a temporary directory outside our allowed root
    outside_path = str(tmp_path / "outside_root.ipynb")
    
    with pytest.raises(PermissionError, match="outside the allowed workspace roots"):
        await notebook_tools_inst.notebook_create(notebook_path=outside_path)
    # Need to create a file to test delete/rename on existing outside file
    # For simplicity, we just test create here. A more robust test would create
    # the file manually and then test delete/rename/read.

async def test_path_validation_wrong_extension(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test that paths without .ipynb extension are rejected."""
    base_path = notebook_path_factory().replace(".ipynb", "")
    txt_path = base_path + ".txt"
    no_ext_path = base_path
    
    with pytest.raises(ValueError, match="must point to a .ipynb file"):
        await notebook_tools_inst.notebook_create(notebook_path=txt_path)
    with pytest.raises(ValueError, match="must point to a .ipynb file"):
        await notebook_tools_inst.notebook_create(notebook_path=no_ext_path)

async def test_path_validation_is_directory(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test that validation fails if the path points to a directory."""
    dir_path = notebook_path_factory()
    # Remove the .ipynb if it exists and create a directory instead
    dir_path = dir_path.replace(".ipynb", "")
    os.makedirs(dir_path, exist_ok=True)
    
    # Re-add .ipynb extension for the test call, pointing to the directory
    path_pointing_to_dir = dir_path + ".ipynb"
    
    # We need to ensure the path check logic runs. 
    # Calling create directly might fail on the directory existing if we don't clean up.
    # A safer approach is to test a read/write operation on a *non-existent* file path
    # whose *parent directory* matches our created directory, IF the validation checks parents.
    # However, the core logic likely checks if the target path *itself* is a file.
    # Let's test `notebook_create` assuming it checks `isfile` or similar on the target.
    
    # Clean up just in case - delete the .ipynb file if it somehow exists
    if os.path.isfile(path_pointing_to_dir):
        os.remove(path_pointing_to_dir)
    # Now create the *directory* with the name we intend to use for the notebook file
    os.makedirs(path_pointing_to_dir, exist_ok=True)

    # Expect FileExistsError because notebook_create checks os.path.exists first
    with pytest.raises(FileExistsError, match=r"Cannot create notebook, file already exists"):
        await notebook_tools_inst.notebook_create(notebook_path=path_pointing_to_dir)
    
    # Clean up the directory we created
    os.rmdir(path_pointing_to_dir)

async def test_add_read_edit_delete_cell(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test adding, reading, editing, and deleting a cell."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    
    # 1. Add a markdown cell
    md_content = "# Initial Cell\nThis is markdown."
    add_md_result = await notebook_tools_inst.notebook_add_cell(
        notebook_path=nb_path,
        cell_type='markdown',
        source=md_content,
        insert_after_index=-1 # Insert at the beginning
    )
    assert "Successfully added markdown cell at index 0" in add_md_result
    
    # Verify cell count
    info = await notebook_tools_inst.notebook_get_info(notebook_path=nb_path)
    assert info['cell_count'] == 1
    
    # 2. Read the cell content
    read_md_content = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=0)
    assert read_md_content == md_content
    
    # 3. Add a code cell after the first
    code_content = "print('hello')"
    add_code_result = await notebook_tools_inst.notebook_add_cell(
        notebook_path=nb_path,
        cell_type='code',
        source=code_content,
        insert_after_index=0 # Insert after the markdown cell
    )
    assert "Successfully added code cell at index 1" in add_code_result
    info = await notebook_tools_inst.notebook_get_info(notebook_path=nb_path)
    assert info['cell_count'] == 2

    # 4. Read the code cell
    read_code_content = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=1)
    assert read_code_content == code_content

    # 5. Edit the markdown cell (index 0)
    edited_md_content = "# Updated Cell Title\n*Emphasis*"
    edit_md_result = await notebook_tools_inst.notebook_edit_cell(
        notebook_path=nb_path,
        cell_index=0,
        source=edited_md_content
    )
    assert "Successfully edited cell 0" in edit_md_result
    read_edited_md = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=0)
    assert read_edited_md == edited_md_content
    
    # 6. Edit the code cell (index 1)
    edited_code_content = "def greet():\n    print('Hello from function!')\ngreet()"
    edit_code_result = await notebook_tools_inst.notebook_edit_cell(
        notebook_path=nb_path,
        cell_index=1,
        source=edited_code_content
    )
    assert "Successfully edited cell 1" in edit_code_result
    read_edited_code = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=1)
    assert read_edited_code == edited_code_content

    # 7. Delete the first cell (markdown)
    delete_result = await notebook_tools_inst.notebook_delete_cell(notebook_path=nb_path, cell_index=0)
    assert "Successfully deleted cell 0" in delete_result
    info = await notebook_tools_inst.notebook_get_info(notebook_path=nb_path)
    assert info['cell_count'] == 1
    
    # Verify the remaining cell is the edited code cell (now at index 0)
    read_remaining = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=0)
    assert read_remaining == edited_code_content
    
    # 8. Delete the last remaining cell
    delete_last_result = await notebook_tools_inst.notebook_delete_cell(notebook_path=nb_path, cell_index=0)
    assert "Successfully deleted cell 0" in delete_last_result
    info = await notebook_tools_inst.notebook_get_info(notebook_path=nb_path)
    assert info['cell_count'] == 0

async def test_cell_index_out_of_bounds(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test operations with invalid cell indices raise IndexError."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='pass', insert_after_index=-1)
    
    # Notebook has 1 cell (index 0)
    invalid_indices = [-1, 1, 100]
    valid_index = 0
    
    for index in invalid_indices:
        with pytest.raises(IndexError):
            await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=index)
        with pytest.raises(IndexError):
            await notebook_tools_inst.notebook_edit_cell(notebook_path=nb_path, cell_index=index, source='new')
        with pytest.raises(IndexError):
            await notebook_tools_inst.notebook_delete_cell(notebook_path=nb_path, cell_index=index)
        # Add cell uses insert_after_index, check its bounds separately
        with pytest.raises(IndexError):
             # Cannot insert after index 1 if only index 0 exists
             await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='', insert_after_index=1)
        with pytest.raises(IndexError):
             # Cannot insert after index -2 (becomes index -1, invalid)
             await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='', insert_after_index=-3)

async def test_add_cell_invalid_type(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test adding a cell with an invalid type fails."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    
    with pytest.raises(ValueError, match="Invalid cell_type"):
        await notebook_tools_inst.notebook_add_cell(
            notebook_path=nb_path,
            cell_type='invalid_type', # Not code or markdown
            source='content',
            insert_after_index=-1
        ) 

# --- Tests for Move, Split, Merge, Change Type, Duplicate ---

async def test_move_cell(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test moving cells within a notebook."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    # Add cells: [MD0, C1, MD2]
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='markdown', source='MD0', insert_after_index=-1)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='C1', insert_after_index=0)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='markdown', source='MD2', insert_after_index=1)
    
    # Move C1 (index 1) to the beginning (index 0)
    # Expected order: [C1, MD0, MD2]
    move_result = await notebook_tools_inst.notebook_move_cell(notebook_path=nb_path, from_index=1, to_index=0)
    assert "Successfully moved cell" in move_result
    cell0 = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=0)
    cell1 = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=1)
    cell2 = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=2)
    assert cell0 == 'C1'
    assert cell1 == 'MD0'
    assert cell2 == 'MD2'

    # Move MD2 (index 2) to the middle (index 1)
    # Expected order: [C1, MD2, MD0]
    move_result_2 = await notebook_tools_inst.notebook_move_cell(notebook_path=nb_path, from_index=2, to_index=1)
    assert "Successfully moved cell" in move_result_2
    cell0_b = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=0)
    cell1_b = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=1)
    cell2_b = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=2)
    assert cell0_b == 'C1'
    assert cell1_b == 'MD2'
    assert cell2_b == 'MD0'
    
    # Test invalid moves
    with pytest.raises(IndexError):
        await notebook_tools_inst.notebook_move_cell(notebook_path=nb_path, from_index=5, to_index=0) # Invalid from
    with pytest.raises(IndexError):
        await notebook_tools_inst.notebook_move_cell(notebook_path=nb_path, from_index=0, to_index=5) # Invalid to

async def test_move_cell_no_op(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test moving a cell to its current location or adjacent is a no-op."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='C0', insert_after_index=-1)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='C1', insert_after_index=0)
    
    # Move C0 to index 0 (its current position)
    result1 = await notebook_tools_inst.notebook_move_cell(notebook_path=nb_path, from_index=0, to_index=0)
    assert "not moved" in result1
    
    # Move C0 to index 1 (immediately after its current position)
    result2 = await notebook_tools_inst.notebook_move_cell(notebook_path=nb_path, from_index=0, to_index=1)
    assert "not moved" in result2

async def test_split_cell(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test splitting a cell into two."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    initial_source = "line1\nline2\nline3\nline4"
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source=initial_source, insert_after_index=-1)
    
    # Split after line 2 (line 3 becomes start of new cell)
    split_result = await notebook_tools_inst.notebook_split_cell(notebook_path=nb_path, cell_index=0, split_at_line=3)
    assert "Successfully split cell" in split_result
    
    info = await notebook_tools_inst.notebook_get_info(notebook_path=nb_path)
    assert info['cell_count'] == 2
    
    cell0_source = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=0)
    cell1_source = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=1)
    
    assert cell0_source == "line1\nline2\n"
    assert cell1_source == "line3\nline4"
    
    # Test invalid splits
    with pytest.raises(ValueError): # split_at_line is out of bounds
        await notebook_tools_inst.notebook_split_cell(notebook_path=nb_path, cell_index=0, split_at_line=0)
    with pytest.raises(ValueError):
        await notebook_tools_inst.notebook_split_cell(notebook_path=nb_path, cell_index=0, split_at_line=10) # Original cell only has 2 lines now
    with pytest.raises(IndexError):
         await notebook_tools_inst.notebook_split_cell(notebook_path=nb_path, cell_index=5, split_at_line=1) # Invalid cell index

async def test_split_cell_at_end(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test splitting a cell at the very end (creates empty second cell)."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    initial_source = "line1\nline2"
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source=initial_source, insert_after_index=-1)
    
    num_lines = len(initial_source.splitlines())
    split_at = num_lines + 1 # Split after the last line
    
    # Split after line 2 (line 3, which doesn't exist, becomes start of new cell)
    split_result = await notebook_tools_inst.notebook_split_cell(notebook_path=nb_path, cell_index=0, split_at_line=split_at)
    assert "Successfully split cell" in split_result
    
    info = await notebook_tools_inst.notebook_get_info(notebook_path=nb_path)
    assert info['cell_count'] == 2
    
    cell0_source = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=0)
    cell1_source = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=1)
    
    assert cell0_source == initial_source # Original cell should be unchanged
    assert cell1_source == "" # New cell should be empty

async def test_split_raw_cell(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test splitting a raw cell."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    # Add markdown, then change to raw
    initial_source = "line1\nline2\nline3"
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='markdown', source=initial_source, insert_after_index=-1)
    await notebook_tools_inst.notebook_change_cell_type(notebook_path=nb_path, cell_index=0, new_type='raw')
    
    # Split the raw cell after line 1
    split_result = await notebook_tools_inst.notebook_split_cell(notebook_path=nb_path, cell_index=0, split_at_line=2)
    assert "Successfully split cell" in split_result
    
    nb = await notebook_tools_inst.read_notebook(nb_path, notebook_tools_inst.config.allowed_roots)
    assert len(nb.cells) == 2
    assert nb.cells[0].cell_type == 'raw'
    assert nb.cells[0].source == "line1\n" # Original cell truncated
    assert nb.cells[1].cell_type == 'raw' # New cell is also raw
    assert nb.cells[1].source == "line2\nline3" # New cell has remaining lines

async def test_merge_cells(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test merging two adjacent cells."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='cell1 line1', insert_after_index=-1)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='cell2 line1\ncell2 line2', insert_after_index=0)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='markdown', source='cell3 md', insert_after_index=1)

    # Merge cell 0 and 1 (both code)
    merge_result = await notebook_tools_inst.notebook_merge_cells(notebook_path=nb_path, first_cell_index=0)
    assert "Successfully merged cell 1 into cell 0" in merge_result
    
    info = await notebook_tools_inst.notebook_get_info(notebook_path=nb_path)
    assert info['cell_count'] == 2 # Should be 2 cells left
    
    merged_cell_source = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=0)
    assert merged_cell_source == "cell1 line1\ncell2 line1\ncell2 line2"
    
    # Verify next cell is still the markdown one
    md_cell_source = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=1)
    assert md_cell_source == "cell3 md"
    
    # Test invalid merges
    with pytest.raises(ValueError, match="different types"):
        # Cannot merge code (index 0) and markdown (index 1)
        await notebook_tools_inst.notebook_merge_cells(notebook_path=nb_path, first_cell_index=0)
    with pytest.raises(IndexError):
        # Cannot merge the last cell (index 1)
        await notebook_tools_inst.notebook_merge_cells(notebook_path=nb_path, first_cell_index=1)
    with pytest.raises(IndexError):
        # Invalid index
        await notebook_tools_inst.notebook_merge_cells(notebook_path=nb_path, first_cell_index=5)

async def test_merge_cells_size_limit(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test merging fails if combined source exceeds size limit."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    
    limit = notebook_tools_inst.config.max_cell_source_size
    # Make source sizes that just exceed the limit when combined
    size1 = limit // 2
    size2 = limit - size1 + 1 
    source1 = "A" * size1
    source2 = "B" * size2
    
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source=source1, insert_after_index=-1)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source=source2, insert_after_index=0)

    with pytest.raises(ValueError, match="Merged source content exceeds maximum allowed size"):
        await notebook_tools_inst.notebook_merge_cells(notebook_path=nb_path, first_cell_index=0)

async def test_merge_cells_different_types(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test merging fails if cells have different types."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='code cell', insert_after_index=-1)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='markdown', source='md cell', insert_after_index=0)
    
    with pytest.raises(ValueError, match="Cannot merge cells of different types"):
        await notebook_tools_inst.notebook_merge_cells(notebook_path=nb_path, first_cell_index=0)

async def test_change_cell_type(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test changing the type of a cell."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='print("code")', insert_after_index=-1)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='markdown', source='# MD', insert_after_index=0)
    
    # Change code (index 0) to markdown
    change1_result = await notebook_tools_inst.notebook_change_cell_type(notebook_path=nb_path, cell_index=0, new_type='markdown')
    assert "Successfully changed cell 0 from 'code' to 'markdown'" in change1_result
    nb = await notebook_tools_inst.read_notebook(nb_path, notebook_tools_inst.config.allowed_roots)
    assert nb.cells[0].cell_type == 'markdown'
    assert nb.cells[0].source == 'print("code")' # Source should remain
    
    # Change original markdown (now index 1) to code
    change2_result = await notebook_tools_inst.notebook_change_cell_type(notebook_path=nb_path, cell_index=1, new_type='code')
    assert "Successfully changed cell 1 from 'markdown' to 'code'" in change2_result
    nb = await notebook_tools_inst.read_notebook(nb_path, notebook_tools_inst.config.allowed_roots)
    assert nb.cells[1].cell_type == 'code'
    assert nb.cells[1].source == '# MD'

    # Change back to original type (should report no change)
    change3_result = await notebook_tools_inst.notebook_change_cell_type(notebook_path=nb_path, cell_index=1, new_type='code')
    assert "already of type 'code'. No change needed" in change3_result

    # Test invalid type
    with pytest.raises(ValueError, match="Invalid cell type"):
        await notebook_tools_inst.notebook_change_cell_type(notebook_path=nb_path, cell_index=0, new_type='graph')
    # Test invalid index
    with pytest.raises(IndexError):
        await notebook_tools_inst.notebook_change_cell_type(notebook_path=nb_path, cell_index=5, new_type='code')

async def test_change_cell_type_no_op(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test changing a cell to the type it already is."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='print(1)', insert_after_index=-1)
    
    # Attempt to change code cell (index 0) to code
    result = await notebook_tools_inst.notebook_change_cell_type(notebook_path=nb_path, cell_index=0, new_type='code')
    
    # Verify success message indicates no change was needed
    assert "already of type 'code'. No change needed" in result

async def test_duplicate_cell(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test duplicating a cell."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='cell 0', insert_after_index=-1)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='markdown', source='cell 1', insert_after_index=0)
    
    # Duplicate cell 0 once
    # Expected: [C0, C0_copy, M1]
    dup1_result = await notebook_tools_inst.notebook_duplicate_cell(notebook_path=nb_path, cell_index=0)
    assert "creating cell after it" in dup1_result
    info = await notebook_tools_inst.notebook_get_info(notebook_path=nb_path)
    assert info['cell_count'] == 3
    cell0 = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=0)
    cell1 = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=1)
    cell2 = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=2)
    assert cell0 == 'cell 0'
    assert cell1 == 'cell 0' # The duplicate
    assert cell2 == 'cell 1'

    # Duplicate cell 2 (markdown) twice
    # Expected: [C0, C0_copy, M1, M1_copy1, M1_copy2]
    dup2_result = await notebook_tools_inst.notebook_duplicate_cell(notebook_path=nb_path, cell_index=2, count=2)
    assert "creating 2 cells after it" in dup2_result
    info = await notebook_tools_inst.notebook_get_info(notebook_path=nb_path)
    assert info['cell_count'] == 5
    cell3 = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=3)
    cell4 = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=4)
    assert cell3 == 'cell 1' # First copy
    assert cell4 == 'cell 1' # Second copy
    
    # Test invalid count
    with pytest.raises(ValueError, match="positive integer"):
        await notebook_tools_inst.notebook_duplicate_cell(notebook_path=nb_path, cell_index=0, count=0)
    with pytest.raises(ValueError, match="positive integer"):
        await notebook_tools_inst.notebook_duplicate_cell(notebook_path=nb_path, cell_index=0, count=-1)
    with pytest.raises(IndexError):
         await notebook_tools_inst.notebook_duplicate_cell(notebook_path=nb_path, cell_index=10)

async def test_raw_cell_handling(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test changing the type to and from raw cells."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='markdown', source='# MD', insert_after_index=-1)
    
    # Change MD (idx 0) to raw
    change1_result = await notebook_tools_inst.notebook_change_cell_type(notebook_path=nb_path, cell_index=0, new_type='raw')
    assert "Successfully changed cell 0 from 'markdown' to 'raw'" in change1_result
    nb = await notebook_tools_inst.read_notebook(nb_path, notebook_tools_inst.config.allowed_roots)
    assert nb.cells[0].cell_type == 'raw'
    assert nb.cells[0].source == '# MD' # Source preserved
    
    # Change raw (idx 0) back to markdown
    change2_result = await notebook_tools_inst.notebook_change_cell_type(notebook_path=nb_path, cell_index=0, new_type='markdown')
    assert "Successfully changed cell 0 from 'raw' to 'markdown'" in change2_result
    nb = await notebook_tools_inst.read_notebook(nb_path, notebook_tools_inst.config.allowed_roots)
    assert nb.cells[0].cell_type == 'markdown'

# --- Tests for Metadata Operations ---

async def test_notebook_metadata(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test reading and editing notebook-level metadata."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    
    # Read initial empty metadata
    metadata = await notebook_tools_inst.notebook_read_metadata(notebook_path=nb_path)
    assert metadata == {}
    
    # Edit metadata - add new keys
    update1 = {"kernelspec": {"name": "python3", "display_name": "Python 3"}, "author": "Test User"}
    edit1_result = await notebook_tools_inst.notebook_edit_metadata(notebook_path=nb_path, metadata_updates=update1)
    assert "Successfully updated metadata" in edit1_result
    
    # Read back and verify
    metadata1 = await notebook_tools_inst.notebook_read_metadata(notebook_path=nb_path)
    assert metadata1 == update1
    
    # Edit metadata - update existing key and add another
    update2 = {"author": "Test User Updated", "language_info": {"name": "python"}}
    edit2_result = await notebook_tools_inst.notebook_edit_metadata(notebook_path=nb_path, metadata_updates=update2)
    assert "Successfully updated metadata" in edit2_result
    
    # Read back and verify merged metadata
    metadata2 = await notebook_tools_inst.notebook_read_metadata(notebook_path=nb_path)
    expected_metadata2 = {
        "kernelspec": {"name": "python3", "display_name": "Python 3"},
        "author": "Test User Updated", # Updated
        "language_info": {"name": "python"} # Added
    }
    assert metadata2 == expected_metadata2

async def test_cell_metadata(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test reading and editing cell-level metadata."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='# Cell 0', insert_after_index=-1)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='markdown', source='# Cell 1', insert_after_index=0)
    
    # Read initial empty metadata for cell 0
    metadata0_initial = await notebook_tools_inst.notebook_read_cell_metadata(notebook_path=nb_path, cell_index=0)
    assert metadata0_initial == {}
    
    # Edit metadata for cell 0
    update0 = {"tags": ["init"], "collapsed": False}
    edit0_result = await notebook_tools_inst.notebook_edit_cell_metadata(notebook_path=nb_path, cell_index=0, metadata_updates=update0)
    assert "Successfully updated metadata for cell 0" in edit0_result
    
    # Read back metadata for cell 0
    metadata0_read = await notebook_tools_inst.notebook_read_cell_metadata(notebook_path=nb_path, cell_index=0)
    assert metadata0_read == update0
    
    # Read initial empty metadata for cell 1
    metadata1_initial = await notebook_tools_inst.notebook_read_cell_metadata(notebook_path=nb_path, cell_index=1)
    assert metadata1_initial == {}

    # Edit metadata for cell 1 - add different keys
    update1 = {"custom_key": "value", "another_tag": True}
    edit1_result = await notebook_tools_inst.notebook_edit_cell_metadata(notebook_path=nb_path, cell_index=1, metadata_updates=update1)
    assert "Successfully updated metadata for cell 1" in edit1_result
    
    # Read back metadata for cell 1
    metadata1_read = await notebook_tools_inst.notebook_read_cell_metadata(notebook_path=nb_path, cell_index=1)
    assert metadata1_read == update1
    
    # Verify metadata for cell 0 hasn't changed
    metadata0_read_again = await notebook_tools_inst.notebook_read_cell_metadata(notebook_path=nb_path, cell_index=0)
    assert metadata0_read_again == update0

    # Test invalid index for cell metadata operations
    with pytest.raises(IndexError):
        await notebook_tools_inst.notebook_read_cell_metadata(notebook_path=nb_path, cell_index=5)
    with pytest.raises(IndexError):
        await notebook_tools_inst.notebook_edit_cell_metadata(notebook_path=nb_path, cell_index=5, metadata_updates={})

# --- Tests for Output Operations ---

async def test_cell_outputs(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test reading and clearing cell outputs."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    
    # Add cells
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='print("Out1")', insert_after_index=-1) # Cell 0
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='markdown', source='MD', insert_after_index=0) # Cell 1
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='1+1', insert_after_index=1) # Cell 2
    
    # Manually add outputs using nbformat
    nb = await notebook_tools_inst.read_notebook(nb_path, notebook_tools_inst.config.allowed_roots)
    # Output for cell 0
    output0 = nbformat.v4.new_output(output_type="stream", name="stdout", text="Out1\n")
    nb.cells[0].outputs = [output0]
    nb.cells[0].execution_count = 1
    # Output for cell 2
    output2_exec = nbformat.v4.new_output(output_type="execute_result", data={"text/plain": "2"}, execution_count=2)
    output2_stream = nbformat.v4.new_output(output_type="stream", name="stderr", text="Warning...")
    nb.cells[2].outputs = [output2_exec, output2_stream]
    nb.cells[2].execution_count = 2
    # Write the notebook back with outputs
    await notebook_tools_inst.write_notebook(nb_path, nb, notebook_tools_inst.config.allowed_roots)

    # 1. Read output from cell 0
    read_outputs0 = await notebook_tools_inst.notebook_read_cell_output(notebook_path=nb_path, cell_index=0)
    assert len(read_outputs0) == 1
    assert read_outputs0[0]['output_type'] == 'stream'
    assert read_outputs0[0]['text'] == 'Out1\n'
    
    # 2. Read output from markdown cell 1 (should be empty)
    read_outputs1 = await notebook_tools_inst.notebook_read_cell_output(notebook_path=nb_path, cell_index=1)
    assert read_outputs1 == []
    
    # 3. Read output from cell 2
    read_outputs2 = await notebook_tools_inst.notebook_read_cell_output(notebook_path=nb_path, cell_index=2)
    assert len(read_outputs2) == 2
    assert read_outputs2[0]['output_type'] == 'execute_result'
    assert read_outputs2[0]['data']['text/plain'] == '2'
    assert read_outputs2[1]['output_type'] == 'stream'
    assert read_outputs2[1]['name'] == 'stderr'

    # 4. Clear output from cell 0
    clear_result0 = await notebook_tools_inst.notebook_clear_cell_outputs(notebook_path=nb_path, cell_index=0)
    assert "Successfully cleared outputs for cell 0" in clear_result0
    read_outputs0_after_clear = await notebook_tools_inst.notebook_read_cell_output(notebook_path=nb_path, cell_index=0)
    assert read_outputs0_after_clear == []
    # Check execution count is also cleared
    nb_check = await notebook_tools_inst.read_notebook(nb_path, notebook_tools_inst.config.allowed_roots)
    assert nb_check.cells[0].execution_count is None
    # Check cell 2 outputs are still there
    read_outputs2_check = await notebook_tools_inst.notebook_read_cell_output(notebook_path=nb_path, cell_index=2)
    assert len(read_outputs2_check) == 2 

    # 5. Clear all outputs
    clear_all_result = await notebook_tools_inst.notebook_clear_all_outputs(notebook_path=nb_path)
    assert "Successfully cleared outputs for 1 code cells" in clear_all_result # Only cell 2 had outputs left
    read_outputs2_after_all_clear = await notebook_tools_inst.notebook_read_cell_output(notebook_path=nb_path, cell_index=2)
    assert read_outputs2_after_all_clear == []
    nb_check2 = await notebook_tools_inst.read_notebook(nb_path, notebook_tools_inst.config.allowed_roots)
    assert nb_check2.cells[2].execution_count is None
    
    # 6. Test invalid index
    with pytest.raises(IndexError):
        await notebook_tools_inst.notebook_read_cell_output(notebook_path=nb_path, cell_index=5)
    with pytest.raises(IndexError):
        await notebook_tools_inst.notebook_clear_cell_outputs(notebook_path=nb_path, cell_index=5)

async def test_read_cell_output_size_limit(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test that reading large outputs returns a truncated representation."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='large_output', insert_after_index=-1)

    # Manually create large output
    large_text = "A" * (notebook_tools_inst.config.max_cell_output_size + 100) 
    large_output_dict = nbformat.v4.new_output(output_type="stream", name="stdout", text=large_text)
    
    nb = await notebook_tools_inst.read_notebook(nb_path, notebook_tools_inst.config.allowed_roots)
    nb.cells[0].outputs = [large_output_dict]
    nb.cells[0].execution_count = 1
    await notebook_tools_inst.write_notebook(nb_path, nb, notebook_tools_inst.config.allowed_roots)

    # Read the output - should be truncated
    read_output = await notebook_tools_inst.notebook_read_cell_output(notebook_path=nb_path, cell_index=0)
    assert len(read_output) == 1
    assert read_output[0]['output_type'] == 'error'
    assert read_output[0]['ename'] == 'OutputSizeError'
    assert "exceeds limit" in read_output[0]['evalue']

# --- Tests for Info, Validate, Export, Full Read ---

async def test_get_info(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Dedicated test for get_info."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='pass', insert_after_index=-1)
    
    # Add some metadata
    metadata = {"kernelspec": {"name": "testkernel"}, "language_info": {"name": "python"}}
    await notebook_tools_inst.notebook_edit_metadata(notebook_path=nb_path, metadata_updates=metadata)
    
    info = await notebook_tools_inst.notebook_get_info(notebook_path=nb_path)
    
    assert isinstance(info, dict)
    assert info['path'] == nb_path
    assert info['cell_count'] == 1
    assert isinstance(info['metadata'], dict)
    assert info['metadata']['kernelspec'] == metadata['kernelspec']
    assert info['kernelspec'] == metadata['kernelspec'] # Check top-level convenience key too
    assert info['language_info'] == metadata['language_info']

async def test_validate(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test notebook validation."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='valid', insert_after_index=-1)

    # Test validation on a valid notebook
    result_valid = await notebook_tools_inst.notebook_validate(notebook_path=nb_path)
    assert "Notebook is valid" in result_valid

    # Manually write invalid JSON to the file to simulate corruption
    try:
        # Read the valid notebook content as text
        with open(nb_path, 'r', encoding='utf-8') as f:
            valid_content_str = f.read()
        # Load as JSON
        nb_dict = json.loads(valid_content_str)
        # Corrupt it (remove required field)
        if nb_dict.get('cells') and len(nb_dict['cells']) > 0:
            nb_dict['cells'][0].pop('cell_type', None)
        else:
            pytest.fail("Test setup issue: Notebook has no cells to corrupt.")
        # Write the corrupted JSON string back to the file
        with open(nb_path, 'w', encoding='utf-8') as f:
            json.dump(nb_dict, f, indent=1)
    except Exception as e:
        pytest.fail(f"Failed to manually corrupt notebook file for test: {e}")

    # Test validation on the invalid notebook
    result_invalid = await notebook_tools_inst.notebook_validate(notebook_path=nb_path)
    assert "Notebook validation failed" in result_invalid
    # Check for the specific error message when cell_type is missing
    assert "is not valid under any of the given schemas" in result_invalid

async def test_read_full_notebook(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test reading the entire notebook structure."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='cell 0', insert_after_index=-1)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='markdown', source='cell 1', insert_after_index=0)
    metadata = {"kernelspec": {"name": "python3"}}
    await notebook_tools_inst.notebook_edit_metadata(notebook_path=nb_path, metadata_updates=metadata)
    
    nb_dict = await notebook_tools_inst.notebook_read(notebook_path=nb_path)
    
    assert isinstance(nb_dict, dict)
    assert nb_dict['nbformat'] == 4 # Check version
    assert 'metadata' in nb_dict
    assert nb_dict['metadata'] == metadata
    assert 'cells' in nb_dict
    assert len(nb_dict['cells']) == 2
    assert nb_dict['cells'][0]['cell_type'] == 'code'
    assert nb_dict['cells'][0]['source'] == 'cell 0'
    assert nb_dict['cells'][1]['cell_type'] == 'markdown'
    assert nb_dict['cells'][1]['source'] == 'cell 1'

# Mark export test - requires nbconvert
@pytest.mark.skipif(not importlib.util.find_spec("nbconvert"), reason="nbconvert not found")
async def test_export_notebook(notebook_tools_inst: NotebookTools, notebook_path_factory, temp_notebook_dir):
    """Test exporting a notebook to various formats."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='print("Hello")', insert_after_index=-1)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='markdown', source='# Title', insert_after_index=0)

    # Test standard, expected-to-work formats
    supported_formats = ['python', 'html', 'markdown']
    for fmt in supported_formats:
        output_filename_base = f"exported_nb_{fmt}"
        # Correct the expected extension for python and markdown formats
        if fmt == 'python':
            expected_extension = ".py"
        elif fmt == 'markdown':
            expected_extension = ".md"
        else:
            expected_extension = f".{fmt}" 
        output_path = str(temp_notebook_dir / (output_filename_base + expected_extension)) # Provide full expected path
        
        export_result = await notebook_tools_inst.notebook_export(
            notebook_path=nb_path, 
            export_format=fmt, 
            output_path=output_path # nbconvert uses basename as --output
        )
        
        assert f"Successfully exported notebook to {fmt} format" in export_result
        # Find the actual generated path from the result message
        actual_output_path = export_result.split(" at ")[-1]
        assert os.path.exists(actual_output_path)
        # Verify the found path is the one we expected (or very similar)
        assert os.path.basename(actual_output_path).startswith(output_filename_base)
        assert actual_output_path.endswith(expected_extension) # Check extension
        # Basic check: ensure file is not empty
        assert os.path.getsize(actual_output_path) > 0

    # Test PDF format - expect failure if LaTeX is missing
    pdf_output_path = str(temp_notebook_dir / "exported_nb_pdf.pdf")
    try:
        pdf_export_result = await notebook_tools_inst.notebook_export(
            notebook_path=nb_path,
            export_format='pdf',
            output_path=pdf_output_path
        )
        # If it succeeds, check the result (LaTeX must be installed)
        assert f"Successfully exported notebook to pdf format" in pdf_export_result
        actual_pdf_path = pdf_export_result.split(" at ")[-1]
        assert os.path.exists(actual_pdf_path)
        assert os.path.getsize(actual_pdf_path) > 0
    except RuntimeError as e:
        # If it fails with RuntimeError, check if it's the expected LaTeX error
        error_message = str(e).lower()
        if "xelatex not found" in error_message or "latex failed" in error_message or "nbconvert failed" in error_message:
            # This is the expected failure if LaTeX isn't installed, so pass the test
            pass 
        else:
            # If it's a different RuntimeError, re-raise it
            pytest.fail(f"PDF export failed with unexpected RuntimeError: {e}")
    except Exception as e:
        # Catch any other unexpected exceptions
        pytest.fail(f"PDF export failed with unexpected exception: {e}")

    # Test exporting outside allowed root (should fail regardless of format)
    with pytest.raises(PermissionError):
         await notebook_tools_inst.notebook_export(notebook_path=nb_path, export_format="python", output_path="/tmp/unsafe_export.py") 

@pytest.mark.skipif(not importlib.util.find_spec("nbconvert"), reason="nbconvert not found")
async def test_export_notebook_same_path(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test exporting fails if output path is same as input path."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    
    with pytest.raises(ValueError, match="Output path cannot be the same as the input"):
        await notebook_tools_inst.notebook_export(
            notebook_path=nb_path,
            export_format="python",
            output_path=nb_path # Using same path for input and output
        )

async def test_clear_all_outputs_no_op(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test clear_all_outputs works correctly when there's nothing to clear."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    # Add only a markdown cell
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='markdown', source='md', insert_after_index=-1)
    
    # Call clear_all_outputs
    result = await notebook_tools_inst.notebook_clear_all_outputs(notebook_path=nb_path)
    
    # Verify success message indicates nothing was cleared
    assert "No code cell outputs found to clear" in result
    
    # Add an empty code cell
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='', insert_after_index=0)
    
    # Call clear_all_outputs again
    result2 = await notebook_tools_inst.notebook_clear_all_outputs(notebook_path=nb_path)
    assert "No code cell outputs found to clear" in result2

async def test_read_large_notebook_truncated(notebook_tools_inst: NotebookTools, temp_notebook_dir):
    """Test reading a large notebook triggers truncation logic when limits are lowered."""
    # Source path for the static fixture
    test_dir = Path(__file__).parent
    static_notebook_source_path = test_dir / "fixtures" / "large_or_malformed_notebook.ipynb"

    if not static_notebook_source_path.exists():
        pytest.skip("Static test file tests/fixtures/large_or_malformed_notebook.ipynb not found.")

    # Destination path inside the allowed temporary directory
    # temp_notebook_dir is provided by conftest.py fixture
    notebook_dest_path = temp_notebook_dir / static_notebook_source_path.name

    # Copy the static file into the allowed directory for the test
    try:
        import shutil
        shutil.copyfile(static_notebook_source_path, notebook_dest_path)
    except Exception as e:
        pytest.fail(f"Failed to copy test fixture to temp dir: {e}")

    # Temporarily lower the size limits for this test using mocking
    low_limit = 1024 # 1 KB limit
    original_config = notebook_tools_inst.config
    
    with mock.patch.object(original_config, 'max_cell_source_size', low_limit), \
         mock.patch.object(original_config, 'max_cell_output_size', low_limit):
             
        # Attempt to read the notebook from the allowed temp directory
        nb_dict = await notebook_tools_inst.notebook_read(notebook_path=str(notebook_dest_path))

        # Assert that truncation occurred 
        global_truncated = nb_dict.get('metadata', {}).get('truncated') is not None
        cell_meta_truncated = any(cell.get('metadata', {}).get('truncated') for cell in nb_dict.get('cells', []))
        cell_source_truncated = any("[Content truncated" in cell.get('source', '') for cell in nb_dict.get('cells', []))
        
        assert global_truncated or cell_meta_truncated or cell_source_truncated, \
               "Notebook read did not indicate truncation when size limits were lowered."

# --- Tests for CLI Entry Point ---

@pytest.mark.asyncio
async def test_cli_entry_point_help(cli_command_path):
    """Test running the installed command with --help."""
    process = await asyncio.create_subprocess_exec(
        cli_command_path,
        '--help',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    stdout = stdout.decode()
    stderr = stderr.decode()

    print(f"CLI --help STDOUT:\n{stdout}")
    print(f"CLI --help STDERR:\n{stderr}")

    assert process.returncode == 0 # Expect clean exit for --help
    assert "usage: cursor-notebook-mcp" in stdout # Check for usage string
    assert "Jupyter Notebook MCP Server" in stdout # Check for description
    # Argparse exits after help, which our main() catches and prints to stderr
    assert "Configuration failed: 0" in stderr 

@pytest.mark.asyncio
async def test_cli_entry_point_no_root(cli_command_path):
    """Test running the installed command without required --allow-root."""
    process = await asyncio.create_subprocess_exec(
        cli_command_path,
        # No arguments provided
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    stdout = stdout.decode()
    stderr = stderr.decode()

    print(f"CLI no-args STDOUT:\n{stdout}")
    print(f"CLI no-args STDERR:\n{stderr}")

    assert process.returncode != 0 # Expect non-zero exit code
    # Check for the argparse error message about missing argument
    assert "the following arguments are required: --allow-root" in stderr
    # Check our specific error message as well
    assert "Configuration failed:" in stderr 

async def test_diagnose_imports(notebook_tools_inst: NotebookTools):
    """Test the diagnostic tool for imports."""
    # This tool doesn't take notebook path etc.
    result = await notebook_tools_inst.diagnose_imports()
    assert isinstance(result, str)
    # Check for expected section headers
    assert "=== Python Environment Diagnostics ===" in result
    assert "=== Module Search Paths (sys.path) ===" in result
    assert "=== nbconvert Detection Tests ===" in result
    assert "=== Checking pip list output ===" in result

async def test_diagnose_imports_pip_not_found(notebook_tools_inst: NotebookTools):
    """Test diagnose_imports when pip command fails (FileNotFoundError)."""
    with mock.patch('subprocess.run', side_effect=FileNotFoundError("pip not found")):
        result = await notebook_tools_inst.diagnose_imports()
        assert "FAILED: 'pip' command not found." in result

async def test_diagnose_imports_pip_timeout(notebook_tools_inst: NotebookTools):
    """Test diagnose_imports when pip list command times out."""
    with mock.patch('subprocess.run', side_effect=subprocess.TimeoutExpired(cmd="pip list", timeout=1)):
        result = await notebook_tools_inst.diagnose_imports()
        assert "FAILED: 'pip list' command timed out." in result

async def test_diagnose_imports_pip_generic_error(notebook_tools_inst: NotebookTools):
    """Test diagnose_imports when pip list command raises a generic Exception."""
    with mock.patch('subprocess.run', side_effect=Exception("Unexpected pip error")):
        result = await notebook_tools_inst.diagnose_imports()
        assert "Error running pip list: Unexpected pip error" in result

async def test_diagnose_imports_no_nbconvert(notebook_tools_inst: NotebookTools):
    """Test diagnose_imports when nbconvert cannot be imported or found."""
    original_import = builtins.__import__ # Store original import function

    def mock_import(name, *args, **kwargs):
        if name == 'nbconvert':
            # Simulate failure for the direct import attempt
            raise ImportError("Mock ImportError: No module named nbconvert")
        # Call original import for other modules to avoid breaking everything
        return original_import(name, *args, **kwargs)

    original_find_spec = importlib.util.find_spec
    def mock_find_spec(name, package=None):
         if name == 'nbconvert':
             # Simulate failure for the find_spec attempt
             return None
         return original_find_spec(name, package)

    # Patch both the import function and find_spec
    with mock.patch('builtins.__import__', side_effect=mock_import), \
         mock.patch('importlib.util.find_spec', side_effect=mock_find_spec):
        result = await notebook_tools_inst.diagnose_imports()

        # Check that both failure messages appear in the result string
        assert "Direct import FAILED: Mock ImportError: No module named nbconvert" in result
        assert "FAILED: No spec found for nbconvert" in result

async def test_add_cell_source_size_limit(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test adding a cell fails if source exceeds size limit."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    
    limit = notebook_tools_inst.config.max_cell_source_size
    large_source = "A" * (limit + 1)
    
    with pytest.raises(ValueError, match="Source content exceeds maximum allowed size"):
        await notebook_tools_inst.notebook_add_cell(
            notebook_path=nb_path,
            cell_type='code',
            source=large_source,
            insert_after_index=-1
        )

async def test_edit_cell_source_size_limit(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test editing a cell fails if source exceeds size limit."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='initial', insert_after_index=-1)

    limit = notebook_tools_inst.config.max_cell_source_size
    large_source = "B" * (limit + 1)
    
    with pytest.raises(ValueError, match="Source content exceeds maximum allowed size"):
        await notebook_tools_inst.notebook_edit_cell(
            notebook_path=nb_path,
            cell_index=0,
            source=large_source
        ) 

async def test_read_cell_source_truncation(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test reading a cell truncates source if it exceeds the configured limit."""
    nb_path = notebook_path_factory()
    limit = notebook_tools_inst.config.max_cell_source_size
    # Create source slightly larger than the limit
    original_large_source = "D" * (limit + 20) # Use different char for clarity
    
    # 1. Create notebook object directly with nbformat
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_code_cell(original_large_source))
    
    # 2. Write this oversized notebook to file, bypassing tool's add_cell check
    try:
        nbformat.write(nb, nb_path)
    except Exception as e:
        pytest.fail(f"Failed to write test notebook file: {e}")
    
    # 3. Read the cell back using the tool method
    read_source = await notebook_tools_inst.notebook_read_cell(notebook_path=nb_path, cell_index=0)
    
    # 4. Verify it was truncated and includes the indicator
    assert len(read_source.encode('utf-8')) < len(original_large_source.encode('utf-8'))
    assert len(read_source.encode('utf-8')) <= limit + 20 # Allow some buffer for suffix/encoding
    assert read_source != original_large_source
    assert read_source.endswith("... (truncated)")

# --- Tests for Error Handling --- 

async def test_notebook_create_io_error(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test that notebook_create handles IOError during write."""
    nb_path = notebook_path_factory()
    
    # Mock write_notebook to raise IOError
    with mock.patch.object(notebook_tools_inst, 'write_notebook', side_effect=IOError("Disk full")):
        # Expect the IOError to be caught and re-raised as RuntimeError or IOError itself
        with pytest.raises((RuntimeError, IOError), match=r"Disk full|unexpected error occurred"):
            await notebook_tools_inst.notebook_create(notebook_path=nb_path)
        
        # Ensure the file was not created (or was cleaned up)
        assert not os.path.exists(nb_path)

async def test_notebook_delete_os_error(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test that notebook_delete handles OSError during os.remove."""
    nb_path = notebook_path_factory()
    # Create the file first so delete can attempt to remove it
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    assert os.path.exists(nb_path)
    
    # Mock os.remove to raise OSError
    with mock.patch('os.remove', side_effect=OSError("Permission denied")):
        # Expect OSError to be caught and re-raised as RuntimeError or IOError
        with pytest.raises((RuntimeError, IOError), match=r"Permission denied|Failed to delete notebook"):
            await notebook_tools_inst.notebook_delete(notebook_path=nb_path)
            
        # Verify the file still exists because the mocked remove failed
        assert os.path.exists(nb_path)

async def test_notebook_rename_source_not_found(notebook_tools_inst: NotebookTools, notebook_path_factory, temp_notebook_dir):
    """Test renaming fails if the source notebook doesn't exist."""
    old_path = notebook_path_factory() # Path is valid but file doesn't exist
    new_path = str(temp_notebook_dir / "new_nonexistent.ipynb")
    
    assert not os.path.exists(old_path)
    
    with pytest.raises(FileNotFoundError):
        await notebook_tools_inst.notebook_rename(old_path=old_path, new_path=new_path)

async def test_notebook_rename_io_error(notebook_tools_inst: NotebookTools, notebook_path_factory, temp_notebook_dir):
    """Test notebook_rename handles IOError/OSError during os.rename."""
    old_path = notebook_path_factory()
    new_path = str(temp_notebook_dir / "rename_target.ipynb")
    await notebook_tools_inst.notebook_create(notebook_path=old_path)
    
    with mock.patch('os.rename', side_effect=OSError("Disk space full")):
        with pytest.raises((RuntimeError, IOError), match=r"Disk space full|Failed to rename"):
            await notebook_tools_inst.notebook_rename(old_path=old_path, new_path=new_path)
        # Ensure original file still exists as rename failed
        assert os.path.exists(old_path)

async def test_notebook_edit_cell_io_error(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test notebook_edit_cell handles IOError during write."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='initial', insert_after_index=-1)

    with mock.patch.object(notebook_tools_inst, 'write_notebook', side_effect=IOError("Write failed")):
        with pytest.raises((RuntimeError, IOError), match=r"Write failed|unexpected error occurred"):
            await notebook_tools_inst.notebook_edit_cell(notebook_path=nb_path, cell_index=0, source='new source')

async def test_clear_cell_outputs_no_op(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test clearing outputs from a code cell with no outputs."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    # Add a code cell, but don't add any outputs
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='print(1)', insert_after_index=-1)

    # Call clear
    result = await notebook_tools_inst.notebook_clear_cell_outputs(notebook_path=nb_path, cell_index=0)

    # Verify success message indicates nothing was cleared
    assert "No outputs or execution count found to clear" in result

async def test_change_cell_type_no_op(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test changing a cell to the type it already is."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='code', source='print(1)', insert_after_index=-1)

    # Attempt to change code cell (index 0) to code
    result = await notebook_tools_inst.notebook_change_cell_type(notebook_path=nb_path, cell_index=0, new_type='code')

    # Verify success message indicates no change was needed
    assert "already of type 'code'. No change needed" in result

async def test_duplicate_raw_cell(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test duplicating a raw cell."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)
    # Change cell 0 to raw
    await notebook_tools_inst.notebook_add_cell(notebook_path=nb_path, cell_type='markdown', source='raw source', insert_after_index=-1)
    await notebook_tools_inst.notebook_change_cell_type(notebook_path=nb_path, cell_index=0, new_type='raw')
    
    # Duplicate the raw cell
    result = await notebook_tools_inst.notebook_duplicate_cell(notebook_path=nb_path, cell_index=0)
    assert "creating cell after it" in result
    
    nb = await notebook_tools_inst.read_notebook(nb_path, notebook_tools_inst.config.allowed_roots)
    assert len(nb.cells) == 2
    assert nb.cells[0].cell_type == 'raw'
    assert nb.cells[1].cell_type == 'raw' # Check duplicate type
    assert nb.cells[1].source == 'raw source' # Check duplicate source

async def test_get_cell_count_generic_exception(notebook_tools_inst: NotebookTools, notebook_path_factory):
    """Test notebook_get_cell_count handles unexpected exceptions."""
    nb_path = notebook_path_factory()
    await notebook_tools_inst.notebook_create(notebook_path=nb_path)

    with mock.patch.object(notebook_tools_inst, 'read_notebook', side_effect=Exception("Unexpected read failure")):
        with pytest.raises(RuntimeError, match=r"An unexpected error occurred"):
            await notebook_tools_inst.notebook_get_cell_count(notebook_path=nb_path)

async def test_notebook_rename_target_is_directory(notebook_tools_inst: NotebookTools, notebook_path_factory, temp_notebook_dir):
    """Test renaming fails if the target path is an existing directory."""
    old_path = notebook_path_factory()
    # Create a directory with the target name
    target_dir_name = "target_dir.ipynb"
    target_path = temp_notebook_dir / target_dir_name
    os.makedirs(target_path, exist_ok=True)
    
    await notebook_tools_inst.notebook_create(notebook_path=old_path)

    # Expect FileExistsError because the path exists, even as a directory
    with pytest.raises(FileExistsError, match=r"Cannot rename notebook, destination already exists"):
         await notebook_tools_inst.notebook_rename(old_path=old_path, new_path=str(target_path))

    # Clean up
    os.rmdir(target_path)

async def test_notebook_rename_target_wrong_extension(notebook_tools_inst: NotebookTools, notebook_path_factory, temp_notebook_dir):
    """Test renaming fails if the target path has the wrong extension."""
    old_path = notebook_path_factory()
    new_path_txt = str(temp_notebook_dir / "new_name.txt")
    await notebook_tools_inst.notebook_create(notebook_path=old_path)

    with pytest.raises(ValueError, match="Both paths must point to .ipynb files"):
         await notebook_tools_inst.notebook_rename(old_path=old_path, new_path=new_path_txt)
