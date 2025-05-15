import pytest
from the_notebook_mcp.tools.tool_utils import (
    extract_code_outline,
    extract_markdown_outline,
    get_first_line_context,
)

# --- Tests for extract_code_outline ---


def test_extract_code_outline_empty():
    assert extract_code_outline("") == []


def test_extract_code_outline_no_defs():
    source = "print('hello')\na = 10"
    assert extract_code_outline(source) == []


def test_extract_code_outline_simple_function():
    source = "def my_func():\n    pass"
    assert extract_code_outline(source) == ["def my_func(...)"]


def test_extract_code_outline_async_function():
    source = "async def my_async_func():\n    pass"
    assert extract_code_outline(source) == ["async def my_async_func(...)"]


def test_extract_code_outline_class():
    source = "class MyClass:\n    pass"
    assert extract_code_outline(source) == ["class MyClass:"]


def test_extract_code_outline_mixed():
    source = (
        "class MyClass:\n"
        "    def __init__(self):\n"
        "        pass\n"
        "\n"
        "def top_level_func():\n"
        "    pass\n"
        "async def another_one():\n"
        "   pass"
    ).replace("\\n", "\n")
    expected = [
        "class MyClass:",
        "def __init__(...)",
        "def top_level_func(...)",
        "async def another_one(...)",
    ]
    # The order might vary depending on ast.walk, so check as sets
    assert set(extract_code_outline(source)) == set(expected)


def test_extract_code_outline_with_syntax_error():
    source = "def my_func()\n pass # Missing colon"
    assert extract_code_outline(source) == []


# --- Tests for extract_markdown_outline ---


def test_extract_markdown_outline_empty():
    assert extract_markdown_outline("") == []


def test_extract_markdown_outline_no_headings():
    source = "This is a normal paragraph.\nAnd another line."
    assert extract_markdown_outline(source) == []


def test_extract_markdown_outline_simple_headings():
    source = "# Header 1\n## Header 2\n### Header 3\n#### Header 4\n##### Header 5\n###### Header 6"
    expected = [
        (1, "Header 1"),
        (2, "Header 2"),
        (3, "Header 3"),
        (4, "Header 4"),
        (5, "Header 5"),
        (6, "Header 6"),
    ]
    assert extract_markdown_outline(source) == expected


def test_extract_markdown_outline_with_text_and_spaces():
    source = "  #  Spaced Header 1  \nSome text\n##Another Header 2\n### Header with ### in it"
    expected = [
        (1, "Spaced Header 1"),
        (3, "Header with ### in it"),
    ]
    assert extract_markdown_outline(source) == expected


def test_extract_markdown_outline_ignore_non_atx():
    source = "Setext Header\n-------------\n# ATX Header\nAnother Setext\n============="
    expected = [(1, "ATX Header")]
    assert extract_markdown_outline(source) == expected


def test_extract_markdown_outline_heading_no_text():
    source = "# \n##"
    assert extract_markdown_outline(source) == []


# --- Tests for get_first_line_context ---


def test_get_first_line_context_empty_source():
    assert get_first_line_context("") == []


def test_get_first_line_context_all_comments_or_empty():
    source = "# Comment 1\n\n# Comment 2\n   \n# Comment 3"
    assert get_first_line_context(source) == []


def test_get_first_line_context_simple():
    source = "line1\nline2\nline3\nline4"
    assert get_first_line_context(source) == ["line1", "line2", "line3"]


def test_get_first_line_context_less_than_max():
    source = "line1\nline2"
    assert get_first_line_context(source) == ["line1", "line2"]


def test_get_first_line_context_with_leading_comments_and_empty():
    source = "# Comment\n\n  \t \nactual_line1\n# Another comment\nactual_line2\nactual_line3\nactual_line4"
    expected = ["actual_line1", "actual_line2", "actual_line3"]
    assert get_first_line_context(source) == expected


def test_get_first_line_context_custom_max_lines():
    source = "l1\nl2\nl3\nl4\nl5"
    assert get_first_line_context(source, max_lines=2) == ["l1", "l2"]
    assert get_first_line_context(source, max_lines=5) == ["l1", "l2", "l3", "l4", "l5"]
    assert get_first_line_context(source, max_lines=10) == [
        "l1",
        "l2",
        "l3",
        "l4",
        "l5",
    ]


def test_get_first_line_context_only_one_valid_line():
    source = "# comment\n\nvalid_line\n# comment 2"
    assert get_first_line_context(source) == ["valid_line"]
