import pytest
import os
import shutil
import asyncio
import nbformat
from pathlib import Path

from the_notebook_mcp.core.config import ServerConfig
from the_notebook_mcp.tools.cell_tools import CellToolsProvider
from the_notebook_mcp.tools.file_tools import FileToolsProvider
from the_notebook_mcp.tools.info_tools import InfoToolsProvider
from the_notebook_mcp.tools.metadata_tools import MetadataToolsProvider
from the_notebook_mcp.tools.output_tools import OutputToolsProvider

# --- Fixtures ---

TEMP_FIXTURE_COPIES_DIR = Path("tests") / "temp_fixture_copies"


@pytest.fixture(scope="session", autouse=True)
def manage_temp_fixture_copies_dir():
    """Creates and cleans up the directory for temporary notebook copies."""
    if TEMP_FIXTURE_COPIES_DIR.exists():
        shutil.rmtree(TEMP_FIXTURE_COPIES_DIR)
    TEMP_FIXTURE_COPIES_DIR.mkdir(parents=True, exist_ok=True)

    yield  # Let the tests run

    if TEMP_FIXTURE_COPIES_DIR.exists():
        shutil.rmtree(TEMP_FIXTURE_COPIES_DIR)


@pytest.fixture(scope="session")
def server_config():
    """Provides a ServerConfig instance for tests."""
    base_path = Path(os.getcwd())

    class MockArgs:
        allow_root = [str(base_path)]  # Workspace root, includes tests/temp_fixture_copies
        log_dir = str(base_path / "tests" / "test_logs")
        log_level_int = 10  # DEBUG
        max_cell_source_size = 1024 * 1024
        max_cell_output_size = 1024 * 1024
        max_notebook_size = 10 * 1024 * 1024
        transport = "stdio"
        host = "127.0.0.1"
        port = 8080
        path = "/mcp"
        config_file = None

    args = MockArgs()
    os.makedirs(args.log_dir, exist_ok=True)
    return ServerConfig(args)


@pytest.fixture(scope="session")
def fixture_notebook_path():
    """Returns the absolute path to the fixture notebook."""
    return os.path.abspath("tests/fixtures/test_notebook.ipynb")


@pytest.fixture
def temp_notebook(fixture_notebook_path, request):
    """Copies the fixture notebook to a temporary location for modification tests, within the workspace."""
    test_name = request.node.name
    # Create a unique filename for each test to avoid conflicts if run in parallel (though not set up for that yet)
    # and to make debugging easier by knowing which test created which file.
    temp_nb_filename = f"temp_{test_name}_{os.urandom(4).hex()}.ipynb"
    temp_nb_path = TEMP_FIXTURE_COPIES_DIR / temp_nb_filename

    shutil.copy2(fixture_notebook_path, temp_nb_path)
    return str(temp_nb_path.resolve())


@pytest.fixture
def cell_tools(server_config):
    return CellToolsProvider(server_config)


@pytest.fixture
def file_tools(server_config):
    return FileToolsProvider(server_config)


@pytest.fixture
def info_tools(server_config):
    return InfoToolsProvider(server_config)


@pytest.fixture
def metadata_tools(server_config):
    return MetadataToolsProvider(server_config)


@pytest.fixture
def output_tools(server_config):
    return OutputToolsProvider(server_config)


# Helper to read notebook directly for assertions
def read_nb_content(path):
    with open(path, "r", encoding="utf-8") as f:
        return nbformat.read(f, as_version=4)


# --- InfoToolsProvider Tests ---


@pytest.mark.asyncio
async def test_notebook_read(info_tools, fixture_notebook_path):
    nb_content = await info_tools.notebook_read(fixture_notebook_path)
    assert nb_content is not None
    assert "cells" in nb_content
    assert len(nb_content["cells"]) > 0
    assert nb_content["nbformat"] == 4


@pytest.mark.asyncio
async def test_notebook_read_cell(info_tools, fixture_notebook_path):
    source = await info_tools.notebook_read_cell(fixture_notebook_path, 0)  # First markdown cell
    assert "# Test Notebook for MCP" in source
    source_code = await info_tools.notebook_read_cell(fixture_notebook_path, 1)  # First code cell
    assert 'print("Hello from cell 1")' in source_code


@pytest.mark.asyncio
async def test_notebook_get_cell_count(info_tools, fixture_notebook_path):
    # Expected count based on the fixture notebook created earlier (10 cells)
    expected_cell_count = 10
    count = await info_tools.notebook_get_cell_count(fixture_notebook_path)
    assert count == expected_cell_count


@pytest.mark.asyncio
async def test_notebook_get_info(info_tools, fixture_notebook_path):
    info = await info_tools.notebook_get_info(fixture_notebook_path)
    assert info["path"] == fixture_notebook_path
    assert info["resolved_path"] == fixture_notebook_path  # Assuming no symlinks for test
    assert info["size_bytes"] > 0
    assert "last_modified" in info
    assert info["cell_count"] == 10  # From fixture
    assert info["nbformat"] == 4
    assert "test_notebook_level_meta" in info["metadata_keys"]


@pytest.mark.asyncio
async def test_notebook_get_outline(info_tools, fixture_notebook_path):
    outline = await info_tools.notebook_get_outline(fixture_notebook_path)
    assert len(outline) > 0
    # Check for a markdown heading
    assert any(item["type"] == "markdown_heading" and item["text"] == "Test Notebook for MCP" for item in outline)
    # Check for a code cell representation (either a definition or context)
    assert any(item["type"] == "code" and 'print("Hello from cell 1")' in item["text"] for item in outline)
    assert any(item["type"] == "code" and "def my_function(...)" in item.get("definitions", []) for item in outline)
    assert any(item["type"] == "code" and "class MyClass:" in item.get("definitions", []) for item in outline)
    assert any(
        item["type"] == "code" and "async def my_async_function(...)" in item.get("definitions", []) for item in outline
    )


@pytest.mark.asyncio
async def test_notebook_search(info_tools, fixture_notebook_path):
    matches = await info_tools.notebook_search(fixture_notebook_path, "Hello from cell 1")
    assert len(matches) == 1
    assert matches[0]["cell_index"] == 1
    assert "Hello from cell 1" in matches[0]["line_content"]

    matches_case = await info_tools.notebook_search(fixture_notebook_path, "hello from cell 1", case_sensitive=False)
    assert len(matches_case) == 1
    assert matches_case[0]["cell_index"] == 1

    matches_not_found = await info_tools.notebook_search(fixture_notebook_path, "string_that_does_not_exist_blah_blah")
    assert len(matches_not_found) == 0


# --- CellToolsProvider Tests ---


@pytest.mark.asyncio
async def test_notebook_edit_cell(cell_tools, temp_notebook):
    new_content = 'print("Updated content!")'
    await cell_tools.notebook_edit_cell(temp_notebook, 1, new_content)
    nb = read_nb_content(temp_notebook)
    assert nb.cells[1].source == new_content


@pytest.mark.asyncio
async def test_notebook_add_cell(cell_tools, temp_notebook):
    initial_nb = read_nb_content(temp_notebook)
    initial_cell_count = len(initial_nb.cells)

    await cell_tools.notebook_add_cell(temp_notebook, "code", 'print("new cell")', insert_after_index=0)
    nb = read_nb_content(temp_notebook)
    assert len(nb.cells) == initial_cell_count + 1
    assert nb.cells[1].cell_type == "code"
    assert nb.cells[1].source == 'print("new cell")'

    await cell_tools.notebook_add_cell(
        temp_notebook, "markdown", "# New MD", insert_after_index=-1
    )  # Insert at beginning
    nb2 = read_nb_content(temp_notebook)
    assert len(nb2.cells) == initial_cell_count + 2
    assert nb2.cells[0].cell_type == "markdown"
    assert nb2.cells[0].source == "# New MD"


@pytest.mark.asyncio
async def test_notebook_delete_cell(cell_tools, temp_notebook):
    # Use a cell known to exist for deletion, e.g., the 9th cell (index 8) "Cell to be deleted."
    target_cell_index_to_delete = 8

    initial_nb = read_nb_content(temp_notebook)
    initial_cell_count = len(initial_nb.cells)
    original_cell_content = initial_nb.cells[target_cell_index_to_delete].source

    await cell_tools.notebook_delete_cell(temp_notebook, target_cell_index_to_delete)

    nb = read_nb_content(temp_notebook)
    assert len(nb.cells) == initial_cell_count - 1
    # Check that the deleted cell is gone and other cells shifted if necessary
    if target_cell_index_to_delete < len(nb.cells):
        assert nb.cells[target_cell_index_to_delete].source != original_cell_content
    else:  # if last cell was deleted
        assert nb.cells[target_cell_index_to_delete - 1].source != original_cell_content


@pytest.mark.asyncio
async def test_notebook_move_cell(cell_tools, temp_notebook):
    # Move cell 9 ("# Cell to be moved\npass") to position 0
    from_idx = 9
    to_idx = 0

    initial_nb = read_nb_content(temp_notebook)
    cell_to_move_source = initial_nb.cells[from_idx].source

    await cell_tools.notebook_move_cell(temp_notebook, from_idx, to_idx)

    nb = read_nb_content(temp_notebook)
    assert nb.cells[to_idx].source == cell_to_move_source
    # Also check that the original cell at to_idx (if not the one moved) is now at to_idx + 1
    # or that the list order has changed as expected.
    # For example, the original cell 0 content should now be at cell 1
    assert nb.cells[to_idx + 1].source == initial_nb.cells[0].source


@pytest.mark.asyncio
async def test_notebook_split_cell(cell_tools, temp_notebook):
    # Split cell 1 ("print(\"Hello from cell 1\")\na = 10") at line 2
    cell_to_split_idx = 1
    split_line = 2  # 1-based line number

    initial_nb = read_nb_content(temp_notebook)
    initial_cell_count = len(initial_nb.cells)

    await cell_tools.notebook_split_cell(temp_notebook, cell_to_split_idx, split_line)

    nb = read_nb_content(temp_notebook)
    assert len(nb.cells) == initial_cell_count + 1
    assert nb.cells[cell_to_split_idx].source == 'print("Hello from cell 1")\n'  # Retains line ending
    assert nb.cells[cell_to_split_idx + 1].source == "a = 10"
    assert nb.cells[cell_to_split_idx].cell_type == "code"
    assert nb.cells[cell_to_split_idx + 1].cell_type == "code"


@pytest.mark.asyncio
async def test_notebook_merge_cells(cell_tools, temp_notebook):
    # Merge cell 0 (markdown) and cell 1 (code) - this should fail as types are different
    # So, let's first add a markdown cell to merge with cell 0
    await cell_tools.notebook_add_cell(temp_notebook, "markdown", "## Second MD Header", insert_after_index=0)

    # Now merge cell 0 and new cell 1 (which was the added markdown)
    initial_nb = read_nb_content(temp_notebook)
    initial_cell_count = len(initial_nb.cells)  # Will be 11 now

    cell1_source = initial_nb.cells[0].source
    cell2_source = initial_nb.cells[1].source

    await cell_tools.notebook_merge_cells(temp_notebook, 0)  # Merge cell 0 and 1

    nb = read_nb_content(temp_notebook)
    assert len(nb.cells) == initial_cell_count - 1
    expected_merged_source = cell1_source + "\n" + cell2_source
    assert nb.cells[0].source == expected_merged_source
    assert nb.cells[0].cell_type == "markdown"


@pytest.mark.asyncio
async def test_notebook_change_cell_type(cell_tools, temp_notebook):
    # Change cell 1 (code) to markdown
    target_idx = 1
    initial_nb = read_nb_content(temp_notebook)
    original_source = initial_nb.cells[target_idx].source

    await cell_tools.notebook_change_cell_type(temp_notebook, target_idx, "markdown")
    nb = read_nb_content(temp_notebook)
    assert nb.cells[target_idx].cell_type == "markdown"
    assert nb.cells[target_idx].source == original_source

    # Change it back to code
    await cell_tools.notebook_change_cell_type(temp_notebook, target_idx, "code")
    nb2 = read_nb_content(temp_notebook)
    assert nb2.cells[target_idx].cell_type == "code"
    assert nb2.cells[target_idx].source == original_source


@pytest.mark.asyncio
async def test_notebook_duplicate_cell(cell_tools, temp_notebook):
    target_idx = 1  # Duplicate the first code cell
    initial_nb = read_nb_content(temp_notebook)
    initial_cell_count = len(initial_nb.cells)
    original_cell_source = initial_nb.cells[target_idx].source

    await cell_tools.notebook_duplicate_cell(temp_notebook, target_idx, count=2)
    nb = read_nb_content(temp_notebook)
    assert len(nb.cells) == initial_cell_count + 2
    assert nb.cells[target_idx].source == original_cell_source  # Original still there
    assert nb.cells[target_idx + 1].source == original_cell_source  # First duplicate
    assert nb.cells[target_idx + 2].source == original_cell_source  # Second duplicate
    assert nb.cells[target_idx + 1].cell_type == initial_nb.cells[target_idx].cell_type
    # Check if outputs/exec_count are cleared for code cell duplicates
    if nb.cells[target_idx + 1].cell_type == "code":
        assert not nb.cells[target_idx + 1].outputs
        assert nb.cells[target_idx + 1].execution_count is None


# --- MetadataToolsProvider Tests ---


@pytest.mark.asyncio
async def test_notebook_read_metadata(metadata_tools, fixture_notebook_path):
    metadata = await metadata_tools.notebook_read_metadata(fixture_notebook_path)
    assert "kernelspec" in metadata
    assert "language_info" in metadata
    assert metadata.get("test_notebook_level_meta") == "global_value"


@pytest.mark.asyncio
async def test_notebook_edit_metadata(metadata_tools, temp_notebook):
    updates = {
        "new_key": "new_value",
        "another_key": 123,
        "test_notebook_level_meta": None,
    }  # Test add, update, delete
    await metadata_tools.notebook_edit_metadata(temp_notebook, updates)
    nb = read_nb_content(temp_notebook)
    assert nb.metadata["new_key"] == "new_value"
    assert nb.metadata["another_key"] == 123
    assert "test_notebook_level_meta" not in nb.metadata


@pytest.mark.asyncio
async def test_notebook_read_cell_metadata(metadata_tools, fixture_notebook_path):
    # Cell 0 (markdown) has {"test_meta_key": "md_global"}
    # Cell 1 (code) has {"tags": ["test", "code"], "custom_key": "value1"}
    meta_md = await metadata_tools.notebook_read_cell_metadata(fixture_notebook_path, 0)
    assert meta_md["test_meta_key"] == "md_global"

    meta_code = await metadata_tools.notebook_read_cell_metadata(fixture_notebook_path, 1)
    assert meta_code["tags"] == ["test", "code"]
    assert meta_code["custom_key"] == "value1"


@pytest.mark.asyncio
async def test_notebook_edit_cell_metadata(metadata_tools, temp_notebook):
    target_idx = 1  # Edit metadata of the first code cell
    updates = {"new_cell_meta": "added", "custom_key": "updated_value", "tags": None}
    await metadata_tools.notebook_edit_cell_metadata(temp_notebook, target_idx, updates)
    nb = read_nb_content(temp_notebook)
    cell_meta = nb.cells[target_idx].metadata
    assert cell_meta["new_cell_meta"] == "added"
    assert cell_meta["custom_key"] == "updated_value"
    assert "tags" not in cell_meta


# --- OutputToolsProvider Tests ---


@pytest.mark.asyncio
async def test_notebook_read_cell_output(output_tools, fixture_notebook_path):
    # Cell 1 has output: stream "Hello from cell 1"
    # Cell 6 has error output
    outputs_cell1 = await output_tools.notebook_read_cell_output(fixture_notebook_path, 1)
    assert len(outputs_cell1) == 1
    assert outputs_cell1[0]["output_type"] == "stream"
    assert "Hello from cell 1" in outputs_cell1[0]["text"]

    outputs_cell6 = await output_tools.notebook_read_cell_output(fixture_notebook_path, 6)
    assert len(outputs_cell6) == 1
    assert outputs_cell6[0]["output_type"] == "error"
    assert outputs_cell6[0]["ename"] == "ZeroDivisionError"

    outputs_no_output_cell = await output_tools.notebook_read_cell_output(
        fixture_notebook_path, 3
    )  # Code cell with no output
    assert len(outputs_no_output_cell) == 0

    # Test markdown cell by expecting a ValueError
    with pytest.raises(ValueError, match="is not a code cell"):
        await output_tools.notebook_read_cell_output(fixture_notebook_path, 0)  # Markdown cell


@pytest.mark.asyncio
async def test_notebook_clear_cell_outputs(output_tools, temp_notebook):
    # Cell 1 has output and execution_count = 1
    target_idx = 1
    await output_tools.notebook_clear_cell_outputs(temp_notebook, target_idx)
    nb = read_nb_content(temp_notebook)
    assert not nb.cells[target_idx].outputs
    assert nb.cells[target_idx].execution_count is None

    # Test on a cell with no output (e.g. cell 3)
    await output_tools.notebook_clear_cell_outputs(temp_notebook, 3)
    nb2 = read_nb_content(temp_notebook)
    assert not nb2.cells[3].outputs
    assert nb2.cells[3].execution_count is None


@pytest.mark.asyncio
async def test_notebook_clear_all_outputs(output_tools, temp_notebook):
    await output_tools.notebook_clear_all_outputs(temp_notebook)
    nb = read_nb_content(temp_notebook)
    for cell in nb.cells:
        if cell.cell_type == "code":
            assert not cell.outputs
            assert cell.execution_count is None


# --- FileToolsProvider Tests ---


@pytest.mark.asyncio
async def test_notebook_create_and_delete(file_tools):
    # Test successful creation
    unique_id = os.urandom(4).hex()
    new_nb_path_str = str((TEMP_FIXTURE_COPIES_DIR / f"created_notebook_{unique_id}.ipynb").resolve())

    result = await file_tools.notebook_create(new_nb_path_str)
    assert os.path.exists(new_nb_path_str)
    assert f"Successfully created new notebook: {new_nb_path_str}" in result
    # Test successful deletion
    result_delete = await file_tools.notebook_delete(new_nb_path_str)
    assert not os.path.exists(new_nb_path_str)
    assert f"Successfully deleted notebook: {new_nb_path_str}" in result_delete


@pytest.mark.asyncio
async def test_notebook_create_errors(file_tools, temp_notebook):
    # temp_notebook provides a valid, existing notebook path from fixture
    existing_nb_path = temp_notebook
    non_abs_path = "relative_path.ipynb"
    outside_root_path = str(Path("/tmp/outside_root.ipynb").resolve())
    invalid_ext_path = str((TEMP_FIXTURE_COPIES_DIR / "invalid_ext.txt").resolve())

    # 1. Non-absolute path
    with pytest.raises(ValueError, match="Only absolute paths are allowed"):
        await file_tools.notebook_create(non_abs_path)

    # 2. Path outside allowed root
    with pytest.raises(
        PermissionError,
        match="Access denied: Path is outside the allowed workspace roots",
    ):
        await file_tools.notebook_create(outside_root_path)

    # 3. Path not ending in .ipynb
    with pytest.raises(ValueError, match="must point to a .ipynb file"):
        await file_tools.notebook_create(invalid_ext_path)

    # 4. File already exists
    with pytest.raises(FileExistsError, match="Cannot create notebook, file already exists"):
        await file_tools.notebook_create(existing_nb_path)


@pytest.mark.asyncio
async def test_notebook_delete_errors(file_tools):
    non_abs_path = "relative_path.ipynb"
    outside_root_path = str(Path("/tmp/outside_root_delete.ipynb").resolve())
    invalid_ext_path = str((TEMP_FIXTURE_COPIES_DIR / "delete_invalid_ext.txt").resolve())
    non_existent_path = str((TEMP_FIXTURE_COPIES_DIR / "non_existent_to_delete.ipynb").resolve())

    # 1. Non-absolute path
    with pytest.raises(ValueError, match="Only absolute paths are allowed"):
        await file_tools.notebook_delete(non_abs_path)

    # 2. Path outside allowed root
    with pytest.raises(
        PermissionError,
        match="Access denied: Path is outside the allowed workspace roots",
    ):
        await file_tools.notebook_delete(outside_root_path)

    # 3. Path not ending in .ipynb
    with pytest.raises(ValueError, match="Path must point to a .ipynb file"):
        await file_tools.notebook_delete(invalid_ext_path)

    # 4. File not found
    with pytest.raises(FileNotFoundError, match="Notebook file not found at"):
        await file_tools.notebook_delete(non_existent_path)


@pytest.mark.asyncio
async def test_notebook_rename_errors(file_tools, temp_notebook):
    original_path = temp_notebook
    non_abs_old_path = "relative_old.ipynb"
    non_abs_new_path = "relative_new.ipynb"
    abs_new_base = TEMP_FIXTURE_COPIES_DIR / "renamed_test"
    os.makedirs(abs_new_base, exist_ok=True)

    # 1. Old path is not absolute
    with pytest.raises(ValueError, match="Only absolute paths are allowed"):
        await file_tools.notebook_rename(non_abs_old_path, str((abs_new_base / "new1.ipynb").resolve()))

    # 2. New path is not absolute
    with pytest.raises(ValueError, match="Only absolute paths are allowed"):
        await file_tools.notebook_rename(original_path, non_abs_new_path)

    # 3. Old path outside allowed root
    outside_old_path = str(Path("/tmp/rename_old_outside.ipynb").resolve())
    with pytest.raises(PermissionError, match="Access denied: One or both paths are outside"):
        await file_tools.notebook_rename(outside_old_path, str((abs_new_base / "new2.ipynb").resolve()))

    # 4. New path outside allowed root
    outside_new_path = str(Path("/tmp/rename_new_outside.ipynb").resolve())
    with pytest.raises(PermissionError, match="Access denied: One or both paths are outside"):
        await file_tools.notebook_rename(original_path, outside_new_path)

    # 5. Old path wrong extension
    wrong_ext_old_path = str((TEMP_FIXTURE_COPIES_DIR / "rename_old_wrong.txt").resolve())
    # Create a dummy file for this test case
    with open(wrong_ext_old_path, "w") as f:
        f.write("dummy")
    with pytest.raises(ValueError, match="Both paths must point to .ipynb files"):
        await file_tools.notebook_rename(wrong_ext_old_path, str((abs_new_base / "new3.ipynb").resolve()))
    if os.path.exists(wrong_ext_old_path):
        os.remove(wrong_ext_old_path)

    # 6. New path wrong extension
    wrong_ext_new_path = str((abs_new_base / "new4_wrong.txt").resolve())
    with pytest.raises(ValueError, match="Both paths must point to .ipynb files"):
        await file_tools.notebook_rename(original_path, wrong_ext_new_path)

    # 7. Source (old_path) does not exist
    non_existent_old_path = str((TEMP_FIXTURE_COPIES_DIR / "non_existent_old_for_rename.ipynb").resolve())
    with pytest.raises(FileNotFoundError, match="Source notebook file not found"):
        await file_tools.notebook_rename(non_existent_old_path, str((abs_new_base / "new5.ipynb").resolve()))

    # 8. Destination (new_path) already exists
    existing_dest_path_str = str((abs_new_base / "existing_dest.ipynb").resolve())
    # Create a dummy file at the destination
    with open(existing_dest_path_str, "w") as f:
        f.write("dummy ipynb")
    with pytest.raises(FileExistsError, match="Cannot rename notebook, destination already exists"):
        await file_tools.notebook_rename(original_path, existing_dest_path_str)
    if os.path.exists(existing_dest_path_str):
        os.remove(existing_dest_path_str)


@pytest.mark.asyncio
async def test_notebook_rename(file_tools, temp_notebook):
    renamed_nb_path_str = str((TEMP_FIXTURE_COPIES_DIR / "renamed_notebook_test.ipynb").resolve())

    initial_content = read_nb_content(temp_notebook)

    await file_tools.notebook_rename(temp_notebook, renamed_nb_path_str)

    assert not Path(temp_notebook).exists()
    assert Path(renamed_nb_path_str).exists()

    renamed_nb_content = read_nb_content(renamed_nb_path_str)
    assert len(renamed_nb_content.cells) == len(initial_content.cells)
    # Clean up
    await file_tools.notebook_delete(renamed_nb_path_str)


@pytest.mark.asyncio
async def test_notebook_validate(file_tools, fixture_notebook_path):
    # Test valid notebook
    result = await file_tools.notebook_validate(fixture_notebook_path)
    assert result == "Notebook format is valid."

    # Test invalid notebook (e.g., missing nbformat minor)
    invalid_nb_path_str = str((TEMP_FIXTURE_COPIES_DIR / "invalid_for_validation.ipynb").resolve())
    # Create a structurally plausible but invalid notebook (e.g. nbformat_minor missing under nbformat=4)
    invalid_content = {
        "cells": [],
        "metadata": {},
        "nbformat": 4,
        # "nbformat_minor": 5, # Missing, will cause validation error
    }
    with open(invalid_nb_path_str, "w", encoding="utf-8") as f:
        nbformat.write(nbformat.from_dict(invalid_content), f)

    result_invalid = await file_tools.notebook_validate(invalid_nb_path_str)
    assert "Notebook validation failed" in result_invalid
    assert "'nbformat_minor' is a required property" in result_invalid

    if os.path.exists(invalid_nb_path_str):
        os.remove(invalid_nb_path_str)

    # Test file not found for validation
    non_existent_path = str((TEMP_FIXTURE_COPIES_DIR / "non_existent_for_validation.ipynb").resolve())
    with pytest.raises(FileNotFoundError):
        await file_tools.notebook_validate(non_existent_path)


@pytest.mark.asyncio
async def test_notebook_export(file_tools, fixture_notebook_path):
    export_formats = ["html", "python", "markdown"]

    for fmt in export_formats:
        output_file_name = f"exported_notebook_test.{fmt}"
        output_file = TEMP_FIXTURE_COPIES_DIR / output_file_name
        abs_output_path = str(output_file.resolve())

        await file_tools.notebook_export(fixture_notebook_path, fmt, abs_output_path)

        assert output_file.exists()
        assert output_file.stat().st_size > 0
        os.remove(output_file)


@pytest.mark.asyncio
async def test_notebook_export_success(file_tools, fixture_notebook_path):
    unique_id = os.urandom(4).hex()
    output_py_path_str = str((TEMP_FIXTURE_COPIES_DIR / f"exported_notebook_{unique_id}.py").resolve())

    result = await file_tools.notebook_export(fixture_notebook_path, "python", output_py_path_str)
    assert os.path.exists(output_py_path_str)
    assert f"Successfully exported notebook to {output_py_path_str}" in result
    with open(output_py_path_str, "r") as f:
        content = f.read()
        assert "# coding: utf-8" in content
        assert "Hello from cell 1" in content
    if os.path.exists(output_py_path_str):
        os.remove(output_py_path_str)


@pytest.mark.asyncio
async def test_notebook_export_overwrite(file_tools, fixture_notebook_path):
    unique_id = os.urandom(4).hex()
    output_path_str = str((TEMP_FIXTURE_COPIES_DIR / f"exported_notebook_overwrite_{unique_id}.html").resolve())

    # Create a dummy file at the output path first
    with open(output_path_str, "w") as f:
        f.write("dummy content to be overwritten")
    assert os.path.exists(output_path_str)

    result = await file_tools.notebook_export(fixture_notebook_path, "html", output_path_str)
    assert os.path.exists(output_path_str)
    assert f"Successfully exported notebook to {output_path_str}" in result
    with open(output_path_str, "r") as f:
        content = f.read()
        assert "dummy content to be overwritten" not in content
        assert "<title>test_notebook</title>" in content
    if os.path.exists(output_path_str):
        os.remove(output_path_str)


@pytest.mark.asyncio
async def test_notebook_export_nbconvert_failure(file_tools, fixture_notebook_path, mocker):
    unique_id = os.urandom(4).hex()
    output_fail_path_str = str((TEMP_FIXTURE_COPIES_DIR / f"exported_notebook_fail_{unique_id}.pdf").resolve())

    # Mock subprocess.run to simulate nbconvert failure
    mock_process = mocker.Mock()
    mock_process.returncode = 1
    mock_process.stderr = "nbconvert error message"
    mock_process.stdout = "nbconvert stdout"
    mocker.patch("subprocess.run", return_value=mock_process)

    with pytest.raises(RuntimeError, match="nbconvert failed"):
        await file_tools.notebook_export(fixture_notebook_path, "pdf", output_fail_path_str)
    assert not os.path.exists(output_fail_path_str)


@pytest.mark.asyncio
async def test_notebook_export_source_not_found(file_tools):
    non_existent_source_path = str((TEMP_FIXTURE_COPIES_DIR / "non_existent_source_for_export.ipynb").resolve())
    output_dest_path = str((TEMP_FIXTURE_COPIES_DIR / "export_dest_will_not_be_created.py").resolve())
    with pytest.raises(FileNotFoundError, match="Source notebook file not found"):
        await file_tools.notebook_export(non_existent_source_path, "python", output_dest_path)


@pytest.mark.asyncio
async def test_notebook_export_error_conditions(file_tools, fixture_notebook_path):
    valid_source = fixture_notebook_path
    valid_output_dir = TEMP_FIXTURE_COPIES_DIR

    # 1. Source path not absolute
    with pytest.raises(ValueError, match="Only absolute paths are allowed"):
        await file_tools.notebook_export(
            "relative_source.ipynb",
            "python",
            str((valid_output_dir / "out1.py").resolve()),
        )

    # 2. Output path not absolute
    with pytest.raises(ValueError, match="Only absolute paths are allowed"):
        await file_tools.notebook_export(valid_source, "python", "relative_output.py")

    # 3. Source path outside allowed root
    outside_source = str(Path("/tmp/export_source_outside.ipynb").resolve())
    with pytest.raises(PermissionError, match="Access denied: One or both paths are outside"):
        await file_tools.notebook_export(outside_source, "python", str((valid_output_dir / "out2.py").resolve()))

    # 4. Output path outside allowed root
    outside_output = str(Path("/tmp/export_output_outside.py").resolve())
    with pytest.raises(PermissionError, match="Access denied: One or both paths are outside"):
        await file_tools.notebook_export(valid_source, "python", outside_output)

    # 5. Source path wrong extension
    dummy_txt_path = str((TEMP_FIXTURE_COPIES_DIR / "dummy_source.txt").resolve())
    with open(dummy_txt_path, "w") as f:
        f.write("text")
    with pytest.raises(ValueError, match="Invalid source file type: Must be a .ipynb file"):
        await file_tools.notebook_export(dummy_txt_path, "python", str((valid_output_dir / "out3.py").resolve()))
    if os.path.exists(dummy_txt_path):
        os.remove(dummy_txt_path)


@pytest.mark.asyncio
async def test_notebook_execute_cell(cell_tools, temp_notebook, mocker):
    """Test executing a cell, mocking the kernel and notebook clients to avoid actual execution."""
    # Mock KernelClient
    mock_kernel = mocker.MagicMock()
    mock_kernel_class = mocker.patch("the_notebook_mcp.tools.cell_tools.KernelClient", return_value=mock_kernel)

    # Mock NbModelClient
    mock_notebook = mocker.MagicMock()
    mock_notebook._doc = mocker.MagicMock()
    mock_notebook._doc._ycells = {
        1: {"outputs": [{"output_type": "stream", "name": "stdout", "text": "Hello from executed cell"}]}
    }
    mock_notebook_class = mocker.patch("the_notebook_mcp.tools.cell_tools.NbModelClient", return_value=mock_notebook)

    # Mock websocket URL function
    mock_ws_url = mocker.patch(
        "the_notebook_mcp.tools.cell_tools.get_jupyter_notebook_websocket_url", return_value="ws://dummy/url"
    )

    # Set up async context managers for the notebook client
    mock_notebook.start = mocker.AsyncMock()
    mock_notebook.stop = mocker.AsyncMock()

    # Test with default server URL
    result = await cell_tools.notebook_execute_cell(temp_notebook, 1)

    # Verify mocks were called correctly
    mock_kernel_class.assert_called_once_with(server_url="http://localhost:8888", token=None)
    mock_kernel.start.assert_called_once()
    mock_notebook_class.assert_called_once_with("ws://dummy/url")
    mock_notebook.start.assert_called_once()
    mock_notebook.execute_cell.assert_called_once_with(1, mock_kernel)
    mock_notebook.stop.assert_called_once()

    # Verify results
    assert len(result) == 1
    assert result[0]["output_type"] == "stream"
    assert result[0]["text"] == "Hello from executed cell"

    # Reset mocks for next test
    mocker.resetall()

    # Test with custom server URL and token
    mock_notebook._doc._ycells = {
        1: {"outputs": [{"output_type": "display_data", "data": {"text/plain": "Display data result"}}]}
    }

    result = await cell_tools.notebook_execute_cell(
        temp_notebook, 1, server_url="http://custom-server:8000", token="test-token"
    )

    # Verify mocks were called with custom parameters
    mock_kernel_class.assert_called_once_with(server_url="http://custom-server:8000", token="test-token")
    assert len(result) == 1
    assert result[0]["output_type"] == "display_data"
    assert result[0]["data"]["text/plain"] == "Display data result"


@pytest.mark.asyncio
async def test_notebook_execute_cell_with_real_server(cell_tools, fixture_notebook_path, mocker):
    """Test the notebook_execute_cell function with mock responses to simulate a real server."""
    # Set up mocks for all the external services

    # 1. Mock KernelClient
    mock_kernel = mocker.MagicMock()
    mock_kernel_class = mocker.patch("the_notebook_mcp.tools.cell_tools.KernelClient", return_value=mock_kernel)

    # 2. Mock get_jupyter_notebook_websocket_url to avoid 404 errors
    mocker.patch(
        "the_notebook_mcp.tools.cell_tools.get_jupyter_notebook_websocket_url",
        return_value="ws://mock-jupyter-server/ws",
    )

    # 3. Mock NbModelClient
    mock_notebook = mocker.MagicMock()
    # Create a realistic structure for _doc._ycells with outputs
    mock_doc = mocker.MagicMock()
    mock_notebook._doc = mock_doc
    mock_notebook._doc._ycells = {
        1: {  # Index of the cell we'll execute - cell 1 is a code cell
            "outputs": [{"output_type": "stream", "name": "stdout", "text": "Hello from cell 1"}]
        }
    }
    mocker.patch("the_notebook_mcp.tools.cell_tools.NbModelClient", return_value=mock_notebook)

    # Set up async context manager behavior
    mock_notebook.start = mocker.AsyncMock()
    mock_notebook.stop = mocker.AsyncMock()
    mock_notebook.execute_cell = mocker.MagicMock()

    # Mock the requests module to emulate responses
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True}
    mocker.patch("requests.get", return_value=mock_response)

    # Run the test with the /lab URL format which should be corrected by our code
    result = await cell_tools.notebook_execute_cell(
        fixture_notebook_path,
        1,  # The cell index to execute (cell 1 is a code cell)
        server_url="http://localhost:8888/lab",  # This URL format should be fixed by the function
        token="test_token",
    )

    # Verify interaction with the kernel client
    mock_kernel.start.assert_called_once()

    # Verify interaction with the notebook client
    mock_notebook.start.assert_called_once()
    mock_notebook.execute_cell.assert_called_once_with(1, mock_kernel)
    mock_notebook.stop.assert_called_once()

    # Verify output
    assert len(result) == 1
    assert result[0]["output_type"] == "stream"
    assert result[0]["name"] == "stdout"
    assert result[0]["text"] == "Hello from cell 1"

    # Test that the URL is passed as-is (with /lab suffix)
    assert mock_kernel_class.call_args.kwargs["server_url"] == "http://localhost:8888/lab"


@pytest.mark.asyncio
async def test_notebook_execute_cell_state_preservation(cell_tools, fixture_notebook_path, mocker):
    """Test that the kernel state is preserved between multiple notebook_execute_cell calls."""
    # Set up mocks for all the external services

    # Mock KernelClient
    mock_kernel = mocker.MagicMock()
    mock_kernel_class = mocker.patch("the_notebook_mcp.tools.cell_tools.KernelClient", return_value=mock_kernel)

    # Mock get_jupyter_notebook_websocket_url
    mocker.patch(
        "the_notebook_mcp.tools.cell_tools.get_jupyter_notebook_websocket_url",
        return_value="ws://mock-jupyter-server/ws",
    )

    # For the first cell (var definition)
    mock_notebook1 = mocker.MagicMock()
    mock_notebook1._doc = mocker.MagicMock()
    mock_notebook1._doc._ycells = {
        1: {
            "outputs": []  # No output for variable definition
        }
    }
    mock_notebook1.start = mocker.AsyncMock()
    mock_notebook1.stop = mocker.AsyncMock()
    mock_notebook1.execute_cell = mocker.MagicMock()

    # For the second cell (using the variable)
    mock_notebook2 = mocker.MagicMock()
    mock_notebook2._doc = mocker.MagicMock()
    mock_notebook2._doc._ycells = {
        3: {"outputs": [{"output_type": "stream", "name": "stdout", "text": "Value of a: 10"}]}
    }
    mock_notebook2.start = mocker.AsyncMock()
    mock_notebook2.stop = mocker.AsyncMock()
    mock_notebook2.execute_cell = mocker.MagicMock()

    # Configure NbModelClient mock to return different instances for the two calls
    nb_client_mock = mocker.patch("the_notebook_mcp.tools.cell_tools.NbModelClient")
    nb_client_mock.side_effect = [mock_notebook1, mock_notebook2]

    # First call to execute cell 1 (defining a variable)
    await cell_tools.notebook_execute_cell(
        fixture_notebook_path,
        1,  # First cell: a = 10 (defined in the first code cell)
        server_url="http://localhost:8888",
        token="test_token",
    )

    # Second call to execute cell 3 (using the variable)
    result = await cell_tools.notebook_execute_cell(
        fixture_notebook_path,
        3,  # Cell 3 is a code cell that can use 'a' from cell 1
        server_url="http://localhost:8888",
        token="test_token",
    )

    # Verify kernel client was created only once
    mock_kernel_class.assert_called_once()

    # Verify both notebook clients were started and stopped
    mock_notebook1.start.assert_called_once()
    mock_notebook1.stop.assert_called_once()
    mock_notebook2.start.assert_called_once()
    mock_notebook2.stop.assert_called_once()

    # Verify both execute_cell calls were made with the same kernel instance
    mock_notebook1.execute_cell.assert_called_once_with(1, mock_kernel)
    mock_notebook2.execute_cell.assert_called_once_with(3, mock_kernel)

    # Verify output of second cell
    assert len(result) == 1
    assert result[0]["output_type"] == "stream"
    assert result[0]["text"] == "Value of a: 10"
