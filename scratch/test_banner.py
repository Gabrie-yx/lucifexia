from rich.console import Console
from lucifex_cli.banner import build_welcome_banner

console = Console()
build_welcome_banner(
    console=console,
    model="gemini-2.5-flash",
    cwd="C:\\Users\\gabri",
    tools=[],
    enabled_toolsets=[],
    session_id="e990876f",
    context_length=8192,
    provider="nous"
)
