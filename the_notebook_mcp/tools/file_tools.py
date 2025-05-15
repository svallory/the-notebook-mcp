"""
Tools for notebook file operations (create, delete, rename, export, validate).
"""

import os
import subprocess
from loguru import logger

import nbformat
import jsonschema

# Import necessary components
from ..core.config import ServerConfig
from ..core import notebook_ops  # Import the module directly


class FileToolsProvider:
    # Update __init__ signature and body
    def __init__(self, config: ServerConfig):
        self.config = config
        # Core ops functions are used directly via notebook_ops.<func_name>
        # mcp_instance is not needed here, registration happens in mcp_setup
        logger.debug("FileToolsProvider initialized.")

    # Update method calls to use imported functions
    async def notebook_create(self, notebook_path: str) -> str:
        """Creates a new, empty Jupyter Notebook (.ipynb) file at the specified path.

        Args:
            notebook_path: The absolute path where the new .ipynb file should be created.
                           Must be within an allowed root directory.
        """
        logger.debug(f"[Tool: notebook_create] Called. Args: path={notebook_path}")

        try:
            # --- Security and Existence Check (Before Write) ---
            if not os.path.isabs(notebook_path):
                raise ValueError("Invalid notebook path: Only absolute paths are allowed.")
            # Use imported notebook_ops.is_path_allowed
            if not notebook_ops.is_path_allowed(notebook_path, self.config.allow_root_dirs):
                raise PermissionError("Access denied: Path is outside the allowed workspace roots.")

            resolved_path = os.path.realpath(notebook_path)
            if not resolved_path.endswith(".ipynb"):
                raise ValueError(f"Invalid file type: '{resolved_path}' must point to a .ipynb file.")
            if os.path.exists(resolved_path):
                raise FileExistsError(f"Cannot create notebook, file already exists: {resolved_path}")

            # --- Create and Write ---
            nb = nbformat.v4.new_notebook()
            # Use imported notebook_ops.write_notebook
            await notebook_ops.write_notebook(notebook_path, nb, self.config.allow_root_dirs)

            logger.info(
                f"[Tool: notebook_create] SUCCESS - Created new notebook at {resolved_path}",
                tool_success=True,
            )
            return f"Successfully created new notebook: {notebook_path}"

        except (
            PermissionError,
            FileExistsError,
            ValueError,
            IOError,
            nbformat.validator.ValidationError,
        ) as e:
            logger.error(f"[Tool: notebook_create] FAILED - {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_create] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred during notebook creation: {e}") from e

    async def notebook_delete(self, notebook_path: str) -> str:
        """Deletes a Jupyter Notebook (.ipynb) file at the specified path.

        Args:
            notebook_path: The absolute path to the notebook file to delete.
                           Must be within an allowed root directory.
        """
        logger.debug(f"[Tool: notebook_delete] Called. Args: path={notebook_path}")

        try:
            # Security Checks
            if not os.path.isabs(notebook_path):
                raise ValueError("Invalid notebook path: Only absolute paths are allowed.")
            if not notebook_ops.is_path_allowed(notebook_path, self.config.allow_root_dirs):
                raise PermissionError("Access denied: Path is outside the allowed workspace roots.")
            if not notebook_path.endswith(".ipynb"):
                raise ValueError("Invalid file type: Path must point to a .ipynb file.")

            resolved_path = os.path.realpath(notebook_path)
            if not os.path.isfile(resolved_path):
                raise FileNotFoundError(f"Notebook file not found at: {resolved_path}")

            # Delete the file
            os.remove(resolved_path)
            logger.info(
                f"[Tool: notebook_delete] SUCCESS - Deleted notebook at {resolved_path}",
                tool_success=True,
            )
            return f"Successfully deleted notebook: {notebook_path}"

        except (ValueError, PermissionError, FileNotFoundError, OSError) as e:
            if isinstance(e, (ValueError, PermissionError, FileNotFoundError)):
                logger.error(f"[Tool: notebook_delete] FAILED - {e}")
                raise
            logger.error(f"[Tool: notebook_delete] FAILED - OS error: {e}")
            raise IOError(f"Failed to delete notebook file due to OS error: {e}") from e
        except Exception as e:
            logger.exception(f"[Tool: notebook_delete] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred during notebook deletion: {e}") from e

    async def notebook_rename(self, old_path: str, new_path: str) -> str:
        """Renames/Moves a Jupyter Notebook (.ipynb) file from one path to another.

        Args:
            old_path: The absolute path to the existing notebook file.
            new_path: The absolute path where the notebook file should be moved/renamed to.
                      Both paths must be within an allowed root directory.
        """
        logger.debug(f"[Tool: notebook_rename] Called. Args: old={old_path}, new={new_path}")

        try:
            # Security Checks
            if not os.path.isabs(old_path) or not os.path.isabs(new_path):
                raise ValueError("Invalid notebook path(s): Only absolute paths are allowed.")
            if not notebook_ops.is_path_allowed(
                old_path, self.config.allow_root_dirs
            ) or not notebook_ops.is_path_allowed(new_path, self.config.allow_root_dirs):
                raise PermissionError("Access denied: One or both paths are outside the allowed workspace roots.")
            if not old_path.endswith(".ipynb") or not new_path.endswith(".ipynb"):
                raise ValueError("Invalid file type: Both paths must point to .ipynb files.")

            resolved_old_path = os.path.realpath(old_path)
            resolved_new_path = os.path.realpath(new_path)

            if not os.path.isfile(resolved_old_path):
                raise FileNotFoundError(f"Source notebook file not found at: {resolved_old_path}")
            if os.path.exists(resolved_new_path):
                raise FileExistsError(f"Cannot rename notebook, destination already exists: {resolved_new_path}")

            # Create parent directory of destination if it doesn't exist
            os.makedirs(os.path.dirname(resolved_new_path), exist_ok=True)

            # Rename/move the file
            os.rename(resolved_old_path, resolved_new_path)
            logger.info(
                f"[Tool: notebook_rename] SUCCESS - Renamed notebook from {resolved_old_path} to {resolved_new_path}",
                tool_success=True,
            )
            return f"Successfully renamed notebook from {old_path} to {new_path}"

        except (
            ValueError,
            PermissionError,
            FileNotFoundError,
            FileExistsError,
            OSError,
        ) as e:
            if isinstance(e, (ValueError, PermissionError, FileNotFoundError, FileExistsError)):
                logger.error(f"[Tool: notebook_rename] FAILED - {e}")
                raise
            logger.error(f"[Tool: notebook_rename] FAILED - OS error: {e}")
            raise IOError(f"Failed to rename notebook file due to OS error: {e}") from e
        except Exception as e:
            logger.exception(f"[Tool: notebook_rename] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred during notebook rename: {e}") from e

    async def notebook_validate(self, notebook_path: str) -> str:
        """Validates a Jupyter Notebook file against the nbformat schema.

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.

        Returns:
            A string indicating "Notebook is valid" or describing the validation errors.
        """
        logger.debug(f"[Tool: notebook_validate] Called. Args: path={notebook_path}")
        try:
            # This will raise ValidationError if invalid
            nb = await notebook_ops.read_notebook(notebook_path, self.config.allow_root_dirs)
            nbformat.validate(nb)  # Explicitly validate after reading
            logger.info(f"[Tool: notebook_validate] SUCCESS - Notebook format is valid.")
            return "Notebook format is valid."
        except (
            nbformat.validator.ValidationError,
            jsonschema.exceptions.ValidationError,
        ) as e:
            logger.error(f"[Tool: notebook_validate] FAILED - Notebook validation error: {e}")
            return f"Notebook validation failed: {e}"
        except (PermissionError, FileNotFoundError, ValueError, IOError) as e:
            logger.error(f"[Tool: notebook_validate] FAILED - Could not read notebook for validation: {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_validate] FAILED - Unexpected error during validation: {e}")
            raise RuntimeError(f"An unexpected error occurred during notebook validation: {e}") from e

    async def notebook_export(self, notebook_path: str, export_format: str, output_path: str) -> str:
        """Exports a Jupyter Notebook to a specified format using nbconvert.

        Args:
            notebook_path: Absolute path to the source .ipynb file.
            export_format: The desired output format (e.g., 'html', 'python', 'pdf', 'markdown').
                           Must be supported by the installed nbconvert.
            output_path: The absolute path for the exported file.
                         Both paths must be within allowed roots.

        Returns:
            A success message string indicating the output path.
        """
        logger.debug(
            f"[Tool: notebook_export] Called. Args: source={notebook_path}, format={export_format}, output={output_path}"
        )

        try:
            # --- Security Checks ---
            if not os.path.isabs(notebook_path) or not os.path.isabs(output_path):
                raise ValueError("Invalid path(s): Only absolute paths are allowed.")
            if not notebook_ops.is_path_allowed(
                notebook_path, self.config.allow_root_dirs
            ) or not notebook_ops.is_path_allowed(output_path, self.config.allow_root_dirs):
                raise PermissionError("Access denied: One or both paths are outside the allowed workspace roots.")
            if not notebook_path.endswith(".ipynb"):
                raise ValueError("Invalid source file type: Must be a .ipynb file.")

            resolved_source_path = os.path.realpath(notebook_path)
            resolved_output_path = os.path.realpath(output_path)

            if not os.path.isfile(resolved_source_path):
                raise FileNotFoundError(f"Source notebook file not found: {resolved_source_path}")
            if os.path.exists(resolved_output_path):
                logger.warning(f"[Tool: notebook_export] Overwriting existing file at {resolved_output_path}")

            os.makedirs(os.path.dirname(resolved_output_path), exist_ok=True)

            # --- nbconvert Execution ---
            cmd = [
                "jupyter",
                "nbconvert",
                "--to",
                export_format,
                "--output",
                resolved_output_path,
                resolved_source_path,
            ]
            logger.debug(f"[Tool: notebook_export] Executing nbconvert command: {' '.join(cmd)}")

            process = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=False)

            if process.returncode != 0:
                error_message = f"nbconvert failed (exit code {process.returncode}).\nStderr: {process.stderr}\nStdout: {process.stdout}"
                logger.error(f"[Tool: notebook_export] FAILED - {error_message}")
                raise RuntimeError(error_message)

            if not os.path.isfile(resolved_output_path):
                expected_dir = os.path.dirname(resolved_output_path)
                base_name_orig_output = os.path.splitext(os.path.basename(resolved_output_path))[0]

                # nbconvert might append its own default extension, esp. for 'python'
                # e.g. --output foo.python --to python -> foo.py (not foo.python.py)
                # or --output foo --to python -> foo.py
                # if --output foo.bar --to python -> foo.bar.py (treats foo.bar as basename)

                # Default expected name if nbconvert respects our full output_path
                possible_output_paths = [resolved_output_path]

                # If export_format is python, nbconvert might take the given output path as a stem and add .py
                if export_format == "python":
                    possible_output_paths.append(resolved_output_path + ".py")
                elif export_format == "markdown":
                    possible_output_paths.append(resolved_output_path + ".md")

                # Check if nbconvert used the basename of output_path and added its default extension
                # e.g. if output_path = /d/file.script and format = 'python', check for /d/file.py
                if export_format == "python":
                    possible_output_paths.append(os.path.join(expected_dir, base_name_orig_output + ".py"))
                else:
                    # For other formats, it might create base_name.export_format
                    possible_output_paths.append(os.path.join(expected_dir, f"{base_name_orig_output}.{export_format}"))

                # Also consider if nbconvert just used the source notebook's basename in the output_dir
                source_basename = os.path.splitext(os.path.basename(resolved_source_path))[0]
                possible_output_paths.append(os.path.join(expected_dir, f"{source_basename}.{export_format}"))
                if export_format == "python":  # And python specific for source basename
                    possible_output_paths.append(os.path.join(expected_dir, f"{source_basename}.py"))

                found_path = None
                for p_path in possible_output_paths:
                    if os.path.isfile(p_path):
                        found_path = p_path
                        break

                if found_path and found_path != resolved_output_path:
                    logger.warning(
                        f"[Tool: notebook_export] nbconvert created {found_path} instead of requested {resolved_output_path}. Renaming."
                    )
                    try:
                        os.rename(found_path, resolved_output_path)
                    except OSError as rename_err:
                        logger.error(
                            f"[Tool: notebook_export] FAILED - Could not rename nbconvert output: {rename_err}"
                        )
                        raise IOError(
                            f"nbconvert created output at {found_path}, but failed to rename to {resolved_output_path}: {rename_err}"
                        ) from rename_err
                elif not os.path.isfile(resolved_output_path):  # Check again after potential rename
                    error_message = f"nbconvert completed but output file not found at expected path: {resolved_output_path} or variations tried: {possible_output_paths}."
                    logger.error(
                        f"[Tool: notebook_export] FAILED - {error_message}\nnbconvert stdout: {process.stdout}\nnbconvert stderr: {process.stderr}"
                    )
                    raise FileNotFoundError(error_message)

            logger.info(
                f"[Tool: notebook_export] SUCCESS - Exported notebook to {resolved_output_path}",
                tool_success=True,
            )
            return f"Successfully exported notebook to {output_path}"

        except (
            ValueError,
            PermissionError,
            FileNotFoundError,
            OSError,
            IOError,
            RuntimeError,
            nbformat.validator.ValidationError,
        ) as e:
            logger.error(f"[Tool: notebook_export] FAILED - {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_export] FAILED - Unexpected error during export: {e}")
            raise RuntimeError(f"An unexpected error occurred during notebook export: {e}") from e
