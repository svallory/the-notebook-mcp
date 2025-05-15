import pytest
import argparse
import sys
from unittest import mock

# Assuming ServerConfig can be instantiated without side effects for version
# or we mock its version attribute if needed.
# For now, let's assume it's okay or mock it if tests fail due to it.
from the_notebook_mcp.core.config import ServerConfig
from the_notebook_mcp.cli import parse_arguments, DEFAULT_LOG_DIR, DEFAULT_LOG_LEVEL_STR

# Store the real ArgumentParser before any patching
RealArgumentParser = argparse.ArgumentParser


# Mock the version for consistency in tests
@pytest.fixture(autouse=True)
def mock_server_config_version():
    with mock.patch("the_notebook_mcp.cli.ServerConfig") as MockServerConfig:
        MockServerConfig.return_value.version = "0.1.0-test"
        yield


def test_parse_arguments_start_defaults():
    """Test 'start' command with minimal args, checking defaults."""
    test_args = ["start", "--allow-root", "/test/dir"]
    with mock.patch.object(sys, "argv", ["prog_name"] + test_args):
        args = parse_arguments()
    assert args.command == "start"
    assert args.allow_root_dirs == ["/test/dir"]
    assert args.log_dir == DEFAULT_LOG_DIR
    assert args.log_level == DEFAULT_LOG_LEVEL_STR
    assert args.max_cell_source_size == 10 * 1024 * 1024
    assert args.max_cell_output_size == 10 * 1024 * 1024
    assert args.transport == "stdio"
    assert args.host == "0.0.0.0"
    assert args.port == 8889
    assert args.path == "/mcp"


def test_parse_arguments_start_all_args():
    """Test 'start' command with all arguments specified."""
    test_args = [
        "start",
        "--allow-root",
        "/test/dir1",
        "--allow-root",
        "/test/dir2",
        "--log-dir",
        "/custom/log",
        "--log-level",
        "DEBUG",
        "--max-cell-source-size",
        "1000",
        "--max-cell-output-size",
        "2000",
        "--transport",
        "sse",
        "--host",
        "127.0.0.1",
        "--port",
        "9999",
        "--path",
        "/custom_mcp",
    ]
    with mock.patch.object(sys, "argv", ["prog_name"] + test_args):
        args = parse_arguments()
    assert args.command == "start"
    assert args.allow_root_dirs == ["/test/dir1", "/test/dir2"]
    assert args.log_dir == "/custom/log"
    assert args.log_level == "DEBUG"  # Test case_insensitive_log_level
    assert args.max_cell_source_size == 1000
    assert args.max_cell_output_size == 2000
    assert args.transport == "sse"
    assert args.host == "127.0.0.1"
    assert args.port == 9999
    assert args.path == "/custom_mcp"


def test_parse_arguments_start_log_level_case_insensitive():
    """Test 'start' command with case-insensitive log level."""
    test_args = ["start", "--allow-root", "/test/dir", "--log-level", "wArNiNg"]
    with mock.patch.object(sys, "argv", ["prog_name"] + test_args):
        args = parse_arguments()
    assert args.log_level == "WARNING"


def test_parse_arguments_start_missing_allow_root():
    """Test 'start' command fails if --allow-root is missing."""
    test_args = ["start", "--log-level", "INFO"]
    with (
        mock.patch.object(sys, "argv", ["prog_name"] + test_args),
        pytest.raises(SystemExit) as excinfo,
    ):
        parse_arguments()
    assert excinfo.value.code != 0  # Should exit with a non-zero code


def test_parse_arguments_version_subcommand():
    """Test 'version' subcommand."""
    test_args = ["version"]
    with mock.patch.object(sys, "argv", ["prog_name"] + test_args):
        args = parse_arguments()
    assert args.command == "version"


def test_parse_arguments_top_level_version_flag():
    """Test top-level --version flag."""
    test_args = ["--version"]
    with (
        mock.patch.object(sys, "argv", ["prog_name"] + test_args),
        pytest.raises(SystemExit) as excinfo,
    ):
        parse_arguments()
    assert excinfo.value.code == 0  # --version action exits with 0


def test_parse_arguments_help_subcommand_no_args():
    """Test 'help' subcommand without arguments."""
    test_args = ["help"]
    with (
        mock.patch.object(sys, "argv", ["prog_name"] + test_args),
        mock.patch("argparse.ArgumentParser.print_help") as mock_print_help,
        pytest.raises(SystemExit) as excinfo,
    ):
        parse_arguments()
    mock_print_help.assert_called_once()
    assert excinfo.value.code == 0


def test_parse_arguments_help_subcommand_with_command():
    """Test 'help' subcommand with a specific command."""
    test_args = ["help", "start"]

    with (
        mock.patch.object(sys, "argv", ["prog_name"] + test_args),
        mock.patch("the_notebook_mcp.cli.argparse.ArgumentParser") as MockArgumentParser,
        pytest.raises(SystemExit) as excinfo,
    ):
        # Get the instance of the ArgumentParser that cli.py creates
        mock_parser_instance = MockArgumentParser.return_value

        # Configure what mock_parser_instance.parse_args() should return
        mock_parsed_args = mock.Mock()
        mock_parsed_args.command = "help"
        mock_parsed_args.cmd_to_help = "start"
        # Add other attributes if parse_arguments accesses them before sys.exit for this path
        mock_parsed_args.help_cmd_show_version = False  # Default for this path
        mock_parser_instance.parse_args.return_value = mock_parsed_args

        # Mock the add_subparsers() method on this instance
        mock_subparsers_action = mock.Mock()
        mock_parser_instance.add_subparsers.return_value = mock_subparsers_action

        # Create a mock for the 'start' subparser
        # Use the real argparse.ArgumentParser for the spec
        mock_start_subparser = mock.Mock(spec=RealArgumentParser)
        mock_start_subparser.print_help = mock.Mock()  # This is what we want to check

        # Set up the .choices attribute on the mock_subparsers_action
        # This dictionary will be returned when cli.py accesses `subparsers.choices`
        mock_subparsers_action.choices = {
            "start": mock_start_subparser,
            "version": mock.Mock(spec=RealArgumentParser, print_help=mock.Mock()),  # Other parsers
            "help": mock.Mock(spec=RealArgumentParser, print_help=mock.Mock()),
        }

        # Call the function under test
        parse_arguments()

    # Assert that print_help was called on our mock_start_subparser
    mock_start_subparser.print_help.assert_called_once()
    assert excinfo.value.code == 0


def test_parse_arguments_help_subcommand_with_unknown_command():
    """Test 'help' subcommand with an unknown command."""
    test_args = ["help", "nonexistentcommand"]
    with (
        mock.patch.object(sys, "argv", ["prog_name"] + test_args),
        mock.patch("builtins.print") as mock_print,
        mock.patch("argparse.ArgumentParser.print_help") as mock_main_print_help,
        pytest.raises(SystemExit) as excinfo,
    ):
        parse_arguments()

    # Check that an error message is printed to stderr (which print does)
    # and that the main help is printed to stderr.
    # argparse prints "invalid choice: 'nonexistentcommand'" to stderr itself
    # then our code prints "Error: Unknown command..."
    # then main help is printed.

    # Check that print was called (for our custom error message)
    # Example: print(f"Error: Unknown command '{parsed_args.cmd_to_help}' for help.\n", file=sys.stderr)
    assert any(
        f"Error: Unknown command 'nonexistentcommand'" in call_args[0][0]
        for call_args in mock_print.call_args_list
        if call_args[0]
    )

    # Check that the main parser's print_help was called (with sys.stderr)
    # In cli.py: parser.print_help(sys.stderr)
    # We check if the first arg of print_help was sys.stderr
    main_help_called_with_stderr = False
    for call in mock_main_print_help.call_args_list:
        if len(call.args) > 0 and call.args[0] == sys.stderr:
            main_help_called_with_stderr = True
            break
    assert main_help_called_with_stderr

    assert excinfo.value.code != 0  # Should exit with non-zero for error


def test_parse_arguments_help_subcommand_with_version_flag():
    """Test 'help --version' subcommand."""
    test_args = ["help", "--version"]
    with mock.patch.object(sys, "argv", ["prog_name"] + test_args):
        args = parse_arguments()
        # server.py handles the actual printing for 'help --version'
        # cli.py just needs to parse it correctly.
    assert args.command == "help"
    assert args.help_cmd_show_version is True
    assert getattr(args, "cmd_to_help", None) is None  # cmd_to_help should not be set


def test_parse_arguments_no_command_provided():
    """Test behavior when no command is provided."""
    test_args = []  # No command
    with (
        mock.patch.object(sys, "argv", ["prog_name"] + test_args),
        mock.patch("argparse.ArgumentParser.print_help") as mock_print_help,
        pytest.raises(SystemExit) as excinfo,
    ):
        parse_arguments()
    mock_print_help.assert_called_once()
    assert excinfo.value.code == 0


def test_case_insensitive_log_level_helper():
    """Test the case_insensitive_log_level helper directly."""
    from the_notebook_mcp.cli import case_insensitive_log_level

    assert case_insensitive_log_level("info") == "INFO"
    assert case_insensitive_log_level("DEBUG") == "DEBUG"
    assert case_insensitive_log_level("WaRnInG") == "WARNING"


# It might be useful to test what happens if ServerConfig raises an error,
# though this is more about ServerConfig's robustness.
# For cli.py, the main concern is that ServerConfig().version is accessed.


def test_parse_arguments_start_invalid_log_level():
    """Test 'start' command with an invalid log level choice."""
    test_args = ["start", "--allow-root", "/test/dir", "--log-level", "INVALIDLEVEL"]
    with (
        mock.patch.object(sys, "argv", ["prog_name"] + test_args),
        pytest.raises(SystemExit) as excinfo,
    ):
        parse_arguments()
    assert excinfo.value.code != 0  # argparse handles invalid choices
