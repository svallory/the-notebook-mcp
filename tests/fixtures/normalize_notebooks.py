#!/usr/bin/env python
"""
Script to normalize notebook test fixtures by adding cell IDs and other required fields.
This helps avoid warnings about missing IDs when running tests.
"""

import nbformat
import uuid
import os
from pathlib import Path


def normalize_notebook(notebook_path):
    """Read a notebook, add cell IDs, and save it back."""
    print(f"Normalizing {notebook_path}")

    # Read the notebook
    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    # Add cell IDs if missing
    for cell in nb.cells:
        if "id" not in cell:
            cell["id"] = str(uuid.uuid4())

    # Save the notebook back
    with open(notebook_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)

    print(f"✓ Added cell IDs to {notebook_path}")


def main():
    """Find and normalize all test notebook fixtures."""
    fixtures_dir = Path("tests/fixtures")

    if not fixtures_dir.exists():
        print(f"Error: {fixtures_dir} directory not found")
        return 1

    notebook_count = 0

    # Process all .ipynb files in fixtures directory
    for notebook_path in fixtures_dir.glob("**/*.ipynb"):
        normalize_notebook(notebook_path)
        notebook_count += 1

    print(f"\nFinished normalizing {notebook_count} notebooks")
    return 0


if __name__ == "__main__":
    exit(main())
