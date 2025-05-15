"""
Handles server branding, including ASCII art and startup messages.
"""

# Using Loguru's color tags for a splash of color.
# Available tags: <red>, <green>, <blue>, <yellow>, <magenta>, <cyan>, <white>,
# <bold>, <underline>, <italic>, <strike>, <dim>, etc.
# Also supports <fg #RRGGBB> and <bg #RRGGBB>.

# Simple ANSI color codes could also be used if Loguru tag processing is an issue
# in some contexts, but tags are generally preferred with Loguru.

from the_notebook_mcp.core.config import ServerConfig


def get_ascii_banner() -> dict:
    """
    Generates a colored ASCII art banner for "The Notebook MCP".
    Uses Loguru color tags and Python logo colors.
    """

    blue = "fg #3776AB"

    orange = "fg #e46e2e"
    banner_lines = [
        "",
        f"<{blue}>         </{blue}><{orange}>▗▖  ▗▖ ▗▄▖ ▗▄▄▄▖▗▄▄▄▖▗▄▄▖  ▗▄▖  ▗▄▖ ▗▖ ▗▖</{orange}><{blue}>         </{blue}>",
        f"<{blue}>┏┳┓┓     </{blue}><{orange}>▐▛▚▖▐▌▐▌ ▐▌  █  ▐▌   ▐▌ ▐▌▐▌ ▐▌▐▌ ▐▌▐▌▗▞▘</{orange}><{blue}>  ┳┳┓┏┓┏┓</{blue}>",
        f"<{blue}> ┃ ┣┓┏┓  </{blue}><{orange}>▐▌ ▝▜▌▐▌ ▐▌  █  ▐▛▀▀▘▐▛▀▚▖▐▌ ▐▌▐▌ ▐▌▐▛▚▖ </{orange}><{blue}>  ┃┃┃┃ ┃┃</{blue}>",
        f"<{blue}> ┻ ┛┗┗   </{blue}><{orange}>▐▌  ▐▌▝▚▄▞▘  █  ▐▙▄▄▖▐▙▄▞▘▝▚▄▞▘▝▚▄▞▘▐▌ ▐▌</{orange}><{blue}>  ┛ ┗┗┛┣┛</{blue}>",
    ]

    return {"width": 59, "text": "\n".join(banner_lines)}


def get_server_startup_message(config: ServerConfig = None) -> str:
    """
    Generates a formatted startup message with ASCII art and connection details.

    Args:
        server_version: Version string
        host: Host address (used for HTTP transports)
        port: Port number (used for HTTP transports)
        transport: Transport protocol (stdio, streamable-http, sse)

    Returns:
        Formatted startup message string
    """

    banner = get_ascii_banner()

    # Center version string after the banner
    version_str = f"Version {config.version}"
    padding_left = (banner["width"] - len(version_str)) // 2
    centered_version = " " * padding_left + version_str

    box_width = banner["width"] - 2
    directories = "\n".join(
        [f"│  - {dir_path} {'':<{box_width - len(dir_path) - 5}}│" for dir_path in config.allow_root_dirs]
    )

    # Format connection information based on transport
    if config.transport == "stdio":
        connection_box = f"""
╭{"─" * box_width}╮
│ <green>Server running</green> <dim>stdio</dim> <yellow>{"Press Ctrl+D to exit":>34}</yellow> │
│{" " * box_width}│
│{" root directories:":<{box_width}}│
{directories}
╰{"─" * box_width}╯
"""
    else:
        # HTTP-based transports (streamable-http or sse)
        url = f"http://{config.host}:{config.port}"
        transport_name = "Streamable HTTP" if config.transport == "streamable-http" else "SSE"
        connection_box = f"""
╭{"─" * box_width}╮
│ <green>Server running</green> <dim>{transport_name}</dim> <yellow>{"Press <lr>Ctrl+C</lr> to exit":>{box_width - len(transport_name) - 9}}</yellow> │
│ URL: <underline>{url}</underline> {"":<{box_width - len(url) - 8}} │
│{" " * box_width}│
│ root directories: {"":<{box_width - 20}} │
{directories}
╰{"─" * box_width}╯
"""

    return f"{banner['text']}\n<magenta>{centered_version}</magenta>\n{connection_box}\n"
