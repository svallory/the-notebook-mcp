import nbformat
from loguru import logger

from ..core import notebook_ops
from ..core.config import ServerConfig


class MetadataToolsProvider:
    """Provides tools for reading and writing notebook and cell metadata."""

    def __init__(self, config: ServerConfig):
        self.config = config
        self.read_notebook = notebook_ops.read_notebook
        self.write_notebook = notebook_ops.write_notebook
        self.is_path_allowed = notebook_ops.is_path_allowed
        logger.debug("MetadataToolsProvider initialized.")

    async def notebook_read_metadata(self, notebook_path: str) -> dict:
        """Reads the top-level metadata of a Jupyter Notebook.

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.

        Returns:
            A dictionary containing the notebook's metadata.
        """
        logger.debug(f"[Tool: notebook_read_metadata] Called. Args: path={notebook_path}")
        try:
            nb = await self.read_notebook(notebook_path, self.config.allow_root_dirs)
            metadata = nb.metadata
            logger.info(
                f"[Tool: notebook_read_metadata] SUCCESS - Read notebook metadata from {notebook_path}.",
                tool_success=True,
            )
            return dict(metadata)  # Return a copy as a plain dict
        except (
            PermissionError,
            FileNotFoundError,
            ValueError,
            nbformat.validator.ValidationError,
            IOError,
        ) as e:
            logger.error(f"[Tool: notebook_read_metadata] FAILED - {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_read_metadata] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred while reading notebook metadata: {e}") from e

    async def notebook_edit_metadata(self, notebook_path: str, metadata_updates: dict) -> str:
        """Updates the top-level metadata of a Jupyter Notebook.

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.
            metadata_updates: A dictionary containing metadata keys and values to update/add.
                              Set a value to None to remove a key.

        Returns:
            A success message string.
        """
        logger.debug(f"[Tool: notebook_edit_metadata] Called. Args: path={notebook_path}, updates={metadata_updates}")
        try:
            nb = await self.read_notebook(notebook_path, self.config.allow_root_dirs)

            # --- Metadata Size Check (Optional but recommended) ---
            # Calculate potential size increase/decrease before modifying?
            # Or just validate after modification before write.

            for key, value in metadata_updates.items():
                if value is None:
                    if key in nb.metadata:
                        del nb.metadata[key]
                        logger.trace(f"[Tool: notebook_edit_metadata] Removed metadata key: {key}")
                else:
                    # Consider validating value type/size here if necessary
                    nb.metadata[key] = value
                    logger.trace(f"[Tool: notebook_edit_metadata] Updated metadata key: {key}")

            # Validate size after update (if applicable, requires serializing)
            # serialized_meta = json.dumps(nb.metadata)
            # if len(serialized_meta.encode('utf-8')) > MAX_METADATA_SIZE:
            #     raise ValueError("Updated metadata exceeds maximum allowed size.")

            await self.write_notebook(notebook_path, nb, self.config.allow_root_dirs)
            logger.info(
                f"[Tool: notebook_edit_metadata] SUCCESS - Updated notebook metadata for {notebook_path}.",
                tool_success=True,
            )
            return "Successfully updated notebook metadata."

        except (
            PermissionError,
            FileNotFoundError,
            ValueError,
            nbformat.validator.ValidationError,
            IOError,
        ) as e:
            logger.error(f"[Tool: notebook_edit_metadata] FAILED - {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_edit_metadata] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred while editing notebook metadata: {e}") from e

    async def notebook_read_cell_metadata(self, notebook_path: str, cell_index: int) -> dict:
        """Reads the metadata of a specific cell in a Jupyter Notebook.

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.
            cell_index: The 0-based index of the cell whose metadata to read.

        Returns:
            A dictionary containing the cell's metadata.
        """
        logger.debug(f"[Tool: notebook_read_cell_metadata] Called. Args: path={notebook_path}, index={cell_index}")
        try:
            nb = await self.read_notebook(notebook_path, self.config.allow_root_dirs)
            if not 0 <= cell_index < len(nb.cells):
                raise IndexError(f"Cell index {cell_index} is out of bounds (0-{len(nb.cells) - 1}).")

            cell = nb.cells[cell_index]
            metadata = cell.metadata
            logger.info(
                f"[Tool: notebook_read_cell_metadata] SUCCESS - Read cell {cell_index} metadata from {notebook_path}.",
                tool_success=True,
            )
            return dict(metadata)  # Return a copy as a plain dict

        except (
            PermissionError,
            FileNotFoundError,
            IndexError,
            ValueError,
            nbformat.validator.ValidationError,
            IOError,
        ) as e:
            logger.error(f"[Tool: notebook_read_cell_metadata] FAILED - {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_read_cell_metadata] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred while reading cell metadata: {e}") from e

    async def notebook_edit_cell_metadata(self, notebook_path: str, cell_index: int, metadata_updates: dict) -> str:
        """Updates the metadata of a specific cell in a Jupyter Notebook.

        Args:
            notebook_path: Absolute path to the .ipynb file within an allowed root.
            cell_index: The 0-based index of the cell to edit.
            metadata_updates: A dictionary containing metadata keys and values to update/add.
                              Set a value to None to remove a key.

        Returns:
            A success message string.
        """
        logger.debug(
            f"[Tool: notebook_edit_cell_metadata] Called. Args: path={notebook_path}, index={cell_index}, updates={metadata_updates}"
        )
        try:
            nb = await self.read_notebook(notebook_path, self.config.allow_root_dirs)
            if not 0 <= cell_index < len(nb.cells):
                raise IndexError(f"Cell index {cell_index} is out of bounds (0-{len(nb.cells) - 1}).")

            cell = nb.cells[cell_index]

            # --- Metadata Size Check (Optional) ---
            # Validate combined size or individual value sizes as needed.

            for key, value in metadata_updates.items():
                if value is None:
                    if key in cell.metadata:
                        del cell.metadata[key]
                        logger.trace(f"[Tool: notebook_edit_cell_metadata] Removed cell metadata key: {key}")
                else:
                    # Consider validating value type/size here if necessary
                    cell.metadata[key] = value
                    logger.trace(f"[Tool: notebook_edit_cell_metadata] Updated cell metadata key: {key}")

            # Validate overall cell size after update? (More complex)

            await self.write_notebook(notebook_path, nb, self.config.allow_root_dirs)
            logger.info(
                f"[Tool: notebook_edit_cell_metadata] SUCCESS - Updated metadata for cell {cell_index} in {notebook_path}.",
                tool_success=True,
            )
            return f"Successfully updated metadata for cell {cell_index}."

        except (
            PermissionError,
            FileNotFoundError,
            IndexError,
            ValueError,
            nbformat.validator.ValidationError,
            IOError,
        ) as e:
            logger.error(f"[Tool: notebook_edit_cell_metadata] FAILED - {e}")
            raise
        except Exception as e:
            logger.exception(f"[Tool: notebook_edit_cell_metadata] FAILED - Unexpected error: {e}")
            raise RuntimeError(f"An unexpected error occurred while editing cell metadata: {e}") from e


# Remove original placeholder comments
# ... existing code ...
