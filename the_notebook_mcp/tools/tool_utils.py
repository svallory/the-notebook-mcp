"""
Utility functions shared among different tool providers.
"""

import ast
import re
from typing import List, Tuple

# --- Outline Generation Helpers ---


def extract_code_outline(source: str) -> List[str]:
    """Extracts function and class definition names from Python code source."""
    defs = []
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                defs.append(f"def {node.name}(...)")
            elif isinstance(node, ast.AsyncFunctionDef):
                defs.append(f"async def {node.name}(...)")
            elif isinstance(node, ast.ClassDef):
                defs.append(f"class {node.name}:")
    except SyntaxError:
        # Ignore code cells that don't parse as valid Python
        pass
    return defs


def extract_markdown_outline(source: str) -> List[Tuple[int, str]]:
    """Extracts ATX-style markdown headings (# ## ### etc.)."""
    headings = []
    lines = source.splitlines()
    # Regex for ATX headings (hashes at the start of a line)
    atx_heading_pattern = re.compile(r"^(#{1,6})\s+(.*)")
    for line in lines:
        match = atx_heading_pattern.match(line.strip())
        if match:
            level = len(match.group(1))  # Number of hashes
            text = match.group(2).strip()
            if text:
                headings.append((level, text))
    return headings


def get_first_line_context(source: str, max_lines: int = 3) -> List[str]:
    """Gets the first few non-empty/non-comment lines of source code for context."""
    lines = source.splitlines()
    context_lines = []
    count = 0
    for line in lines:
        stripped_line = line.strip()
        if stripped_line and not stripped_line.startswith("#"):
            context_lines.append(line)  # Return original line
            count += 1
            if count >= max_lines:
                break
    return context_lines
