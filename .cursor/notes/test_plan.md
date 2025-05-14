# Test Plan for the-notebook-mcp

## Goal
Ensure all MCP tools provided by `the-notebook-mcp` are functioning correctly and are covered by automated tests.

## Tools and Test Status

| Tool                          | Tested In (`test_notebook_tools.py`) | Notes                                                                 |
| ----------------------------- | ------------------------------------ | --------------------------------------------------------------------- |
| `notebook_create`             | `test_notebook_create_and_delete`    | Covered                                                               |
| `notebook_delete`             | `test_notebook_create_and_delete`    | Covered                                                               |
| `notebook_rename`             | `test_notebook_rename`               | Covered                                                               |
| `notebook_read`               | `test_notebook_read`                 | Covered                                                               |
| `notebook_read_cell`          | `test_notebook_read_cell`            | Covered                                                               |
| `notebook_add_cell`           | `test_notebook_add_cell`             | Covered                                                               |
| `notebook_edit_cell`          | `test_notebook_edit_cell`            | Covered                                                               |
| `notebook_delete_cell`        | `test_notebook_delete_cell`          | Covered                                                               |
| `notebook_change_cell_type`   | `test_notebook_change_cell_type`     | Covered                                                               |
| `notebook_duplicate_cell`     | `test_notebook_duplicate_cell`       | Covered                                                               |
| `notebook_get_cell_count`     | `test_notebook_get_cell_count`       | Covered                                                               |
| `notebook_read_metadata`      | `test_notebook_read_metadata`        | Covered                                                               |
| `notebook_edit_metadata`      | `test_notebook_edit_metadata`        | Covered                                                               |
| `notebook_read_cell_metadata` | `test_notebook_read_cell_metadata`   | Covered                                                               |
| `notebook_edit_cell_metadata` | `test_notebook_edit_cell_metadata`   | Covered                                                               |
| `notebook_read_cell_output`   | `test_notebook_read_cell_output`     | Covered                                                               |
| `notebook_clear_cell_outputs` | `test_notebook_clear_cell_outputs`   | Covered                                                               |
| `notebook_clear_all_outputs`  | `test_notebook_clear_all_outputs`    | Covered                                                               |
| `notebook_move_cell`          | `test_notebook_move_cell`            | Covered                                                               |
| `notebook_split_cell`         | `test_notebook_split_cell`           | Covered                                                               |
| `notebook_merge_cells`        | `test_notebook_merge_cells`          | Partially tested (fails on different types). Needs success case tests. |
| `notebook_validate`           | `test_notebook_validate`             | Covered                                                               |
| `notebook_get_info`           | `test_notebook_get_info`             | Covered                                                               |
| `notebook_export`             | `test_notebook_export`               | Covered                                                               |
| `notebook_get_outline`        | `test_notebook_get_outline`          | Covered (InfoToolsProvider)                                           |
| `notebook_search`             | `test_notebook_search`               | Covered (InfoToolsProvider)                                           |
| `diagnose_imports`            | `test_diagnose_imports`              | Covered (DiagnosticToolsProvider)                                     |

## Tasks

### Test Creation/Enhancement
1.  **`notebook_merge_cells`**:
    *   Add test cases for successful merges of code cells.
    *   Add test cases for successful merges of markdown cells.
    *   Test merging the first cell with the second.
    *   Test merging the second-to-last cell with the last.
    *   Test attempting to merge the last cell (should likely fail or be a no-op, clarify behavior and test).
2.  **Review Existing Tests**:
    *   Systematically review each test function in `test_notebook_tools.py`.
    *   For each tool, verify that tests cover:
        *   Happy path scenarios.
        *   Common edge cases (e.g., empty notebooks, single cell notebooks, large inputs if applicable).
        *   Invalid inputs and error handling (e.g., incorrect file paths, out-of-bounds indices).
        *   Idempotency where applicable.
        *   Correctness of changes to the notebook file content.

### Test Setup Verification
*   [ ] Check `pyproject.toml` for test dependencies and pytest configuration. (Done - Seems OK)
*   [ ] Check `run_tests.sh` script. (Done - Seems OK)
*   [ ] Ensure test environment setup (e.g., `uv pip install -e ".[dev]"`) is documented and clear. (Done - README covers this)

### Test Execution and Results
*   [ ] Run all existing tests.
*   [ ] Document Pass/Fail status for each test suite/tool.

## Test Results (To be filled after execution)

*   `test_notebook_tools.py`: All 25 tests PASSED.
    *   `test_notebook_read`: PASSED
    *   `test_notebook_read_cell`: PASSED
    *   `test_notebook_get_cell_count`: PASSED
    *   `test_notebook_get_info`: PASSED
    *   `test_notebook_get_outline`: PASSED
    *   `test_notebook_search`: PASSED
    *   `test_notebook_edit_cell`: PASSED
    *   `test_notebook_add_cell`: PASSED
    *   `test_notebook_delete_cell`: PASSED
    *   `test_notebook_move_cell`: PASSED
    *   `test_notebook_split_cell`: PASSED
    *   `test_notebook_merge_cells`: PASSED (Initial check for failure on different types. Further checks for success cases are in tasks.)
    *   `test_notebook_change_cell_type`: PASSED
    *   `test_notebook_duplicate_cell`: PASSED
    *   `test_notebook_read_metadata`: PASSED
    *   `test_notebook_edit_metadata`: PASSED
    *   `test_notebook_read_cell_metadata`: PASSED
    *   `test_notebook_edit_cell_metadata`: PASSED
    *   `test_notebook_read_cell_output`: PASSED
    *   `test_notebook_clear_cell_outputs`: PASSED
    *   `test_notebook_clear_all_outputs`: PASSED
    *   `test_notebook_create_and_delete`: PASSED
    *   `test_notebook_rename`: PASSED
    *   `test_notebook_validate`: PASSED
    *   `test_notebook_export`: PASSED
    *   `test_diagnose_imports`: PASSED
*   `test_tool_utils.py`: All 21 tests PASSED.

---
This note will be updated as tasks are completed. 