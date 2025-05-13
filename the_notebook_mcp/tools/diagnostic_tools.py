import sys
import importlib.util

from loguru import logger

from ..core.config import ServerConfig

class DiagnosticToolsProvider:
    """Provides MCP tools for diagnostics."""
    def __init__(self, config: ServerConfig):
        self.config = config
        logger.debug("DiagnosticToolsProvider initialized.")

    async def diagnose_imports(self) -> str:
        """Checks if essential libraries (nbformat, etc.) are importable and logs details.

        Returns:
            A string summarizing the diagnostic results.
        """
        logger.debug("[Tool: diagnose_imports] Running import diagnostics...")
        results = []
        status = "OK"

        libraries_to_check = [
            ("nbformat", "Core notebook format handling"),
            ("nbconvert", "Notebook exporting functionality"),
            ("fastmcp", "MCP server framework"),
            ("uvicorn", "ASGI server"),
            ("starlette", "ASGI framework"),
            ("sse_starlette", "Server-Sent Events helper"),
        ]

        for lib_name, description in libraries_to_check:
            try:
                spec = importlib.util.find_spec(lib_name)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module) # type: ignore
                    version = getattr(module, '__version__', 'N/A')
                    path = getattr(spec, 'origin', 'N/A')
                    results.append(f"  [PASS] {lib_name} (v{version}): {description}")
                    logger.trace(f"[Tool: diagnose_imports] Found {lib_name} v{version} at {path}")
                else:
                    results.append(f"  [FAIL] {lib_name}: Not found - {description}")
                    logger.error(f"[Tool: diagnose_imports] Could not find {lib_name}.")
                    status = "FAIL"
            except ImportError as e:
                results.append(f"  [FAIL] {lib_name}: Import error '{e}' - {description}")
                logger.error(f"[Tool: diagnose_imports] Import error for {lib_name}: {e}")
                status = "FAIL"
            except Exception as e:
                results.append(f"  [ERROR] {lib_name}: Unexpected error during check '{e}' - {description}")
                logger.exception(f"[Tool: diagnose_imports] Unexpected error checking {lib_name}: {e}")
                status = "ERROR"

        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        summary = (
            f"Import Diagnostics ({status}):\n"
            f"Python Version: {python_version}\n"
            + "\n".join(results)
        )

        logger.info(f"[Tool: diagnose_imports] SUCCESS - Diagnostics complete. Status: {status}", tool_success=True)
        return summary

    # Methods to be moved here:
    # async def diagnose_imports(self) -> str: 