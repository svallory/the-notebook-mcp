"""
Handles server branding, including ASCII art and startup messages.
"""

# Using Loguru's color tags for a splash of color.
# Available tags: <red>, <green>, <blue>, <yellow>, <magenta>, <cyan>, <white>,
# <bold>, <underline>, <italic>, <strike>, <dim>, etc.
# Also supports <fg #RRGGBB> and <bg #RRGGBB>.

# Simple ANSI color codes could also be used if Loguru tag processing is an issue
# in some contexts, but tags are generally preferred with Loguru.

def get_ascii_banner() -> dict:
    """
    Generates a colored ASCII art banner for "The Notebook MCP".
    Uses Loguru color tags and Python logo colors.
    """
    # Simpler, hollow-style banner using Python colors
    blue = "fg #3776AB"
    # yellow: <fg #FFD43B>
    orange = "fg #e46e2e"
    banner_lines = [
        "",
        f"<{blue}>         </{blue}><{orange}>▗▖  ▗▖ ▗▄▖ ▗▄▄▄▖▗▄▄▄▖▗▄▄▖  ▗▄▖  ▗▄▖ ▗▖ ▗▖</{orange}><{blue}>         </{blue}>",
        f"<{blue}>┏┳┓┓     </{blue}><{orange}>▐▛▚▖▐▌▐▌ ▐▌  █  ▐▌   ▐▌ ▐▌▐▌ ▐▌▐▌ ▐▌▐▌▗▞▘</{orange}><{blue}>  ┳┳┓┏┓┏┓</{blue}>",
        f"<{blue}> ┃ ┣┓┏┓  </{blue}><{orange}>▐▌ ▝▜▌▐▌ ▐▌  █  ▐▛▀▀▘▐▛▀▚▖▐▌ ▐▌▐▌ ▐▌▐▛▚▖ </{orange}><{blue}>  ┃┃┃┃ ┃┃</{blue}>",
        f"<{blue}> ┻ ┛┗┗   </{blue}><{orange}>▐▌  ▐▌▝▚▄▞▘  █  ▐▙▄▄▖▐▙▄▞▘▝▚▄▞▘▝▚▄▞▘▐▌ ▐▌</{orange}><{blue}>  ┛ ┗┗┛┣┛</{blue}>",
    ]
    
    # Use actual newline characters, not escaped ones
    return {
        "width": 59,
        "text": "\n".join(banner_lines)
    }

def get_server_startup_message(
    server_version: str,
    host: str = None,
    port: int = None,
    transport: str = "stdio"
) -> str:
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
    
    # Get the banner
    banner = get_ascii_banner()
    
    # Center version string after the banner
    version_str = f"Version {server_version}"
    padding_left = (banner['width'] - len(version_str)) // 2
    centered_version = " " * padding_left + version_str
    
    # Format connection information based on transport
    if transport == "stdio":
        connection_box = f"""
╭{"─" * (banner['width'] - 2)}╮
│ Transport: STDIO {"" :<{banner['width'] - 21}} │
│ <green>Server running</green> <yellow>{"Press Ctrl+D to exit":>40}</yellow> │
╰{"─" * (banner['width'] - 2)}╯
"""
    else:
        # HTTP-based transports (streamable-http or sse)
        url = f"http://{host}:{port}"
        transport_name = "Streamable HTTP" if transport == "streamable-http" else "Server-Sent Events (SSE)"
        connection_box = f"""
╭{"─" * (banner['width'] - 2)}╮
│ Transport: {transport_name}{"" :<{banner['width'] - 15 - len(transport_name)}} │
│ Server URL: {url}{"" :<{banner['width'] - 16 - len(url)}} │
│ <green>Server running</green> <yellow>{"Press <lr>Ctrl+C</lr> to exit":>49}</yellow> │
╰{"─" * (banner['width'] - 2)}╯
"""

    # Combine the ASCII art, centered version and connection box
    return f"{banner['text']}\n<magenta>{centered_version}</magenta>\n{connection_box}\n"