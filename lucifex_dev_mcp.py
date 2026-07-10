#!/usr/bin/env python3
import sys
import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Configure logging to stderr so it does not corrupt stdio transport
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
logger = logging.getLogger("lucifex-dev-mcp")

# Ensure workspace root is in path
workspace_root = Path(__file__).parent.absolute()
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Error: 'mcp' library not found. Install it in the python environment.", file=sys.stderr)
    sys.exit(1)

mcp = FastMCP(
    "lucifex-dev",
    instructions=(
        "Lucifex Development and Inter-agent Communication MCP Server.\n"
        "Allows direct chat with the Lucifex AI Agent and execution of Lucifex CLI commands "
        "to coordinate actions, share context, and run pair programming tasks."
    )
)

# Cache for AIAgent instances by session ID
_agents: Dict[str, Any] = {}

def get_or_create_agent(session_id: Optional[str] = None) -> Any:
    sid = session_id or "default-dev-mcp-session"
    if sid not in _agents:
        logger.info(f"Initializing new Lucifex AIAgent for session: {sid}")
        
        from lucifex_cli.config import load_config
        from lucifex_cli.runtime_provider import resolve_runtime_provider
        from run_agent import AIAgent
        
        cfg = load_config()
        
        # Resolve model
        model_cfg = cfg.get("model") or {}
        if isinstance(model_cfg, str):
            cfg_model = model_cfg
        else:
            cfg_model = model_cfg.get("default") or model_cfg.get("model") or ""
            
        env_model = os.getenv("LUCIFEX_INFERENCE_MODEL", "").strip()
        effective_model = env_model or cfg_model
        
        # Resolve provider
        cfg_provider = ""
        if isinstance(model_cfg, dict):
            cfg_provider = str(model_cfg.get("provider") or "").strip().lower()
        current_provider = (
            cfg_provider
            or os.getenv("LUCIFEX_INFERENCE_PROVIDER", "").strip().lower()
            or "auto"
        )
        
        runtime = resolve_runtime_provider(
            requested=current_provider,
            target_model=effective_model or None,
        )
        
        # Build the AIAgent instance using the resolved parameters
        _agents[sid] = AIAgent(
            session_id=sid,
            api_key=runtime.get("api_key"),
            base_url=runtime.get("base_url"),
            provider=runtime.get("provider"),
            api_mode=runtime.get("api_mode"),
            model=effective_model,
            credential_pool=runtime.get("credential_pool"),
            save_trajectories=True,
        )
    return _agents[sid]

@mcp.tool()
def ask_lucifex(prompt: str, session_id: Optional[str] = None) -> str:
    """Send a prompt/message directly to the Lucifex AI Agent and get its response.
    
    This allows you to converse with the Lucifex Agent, delegate subtasks, or align on goals.
    
    Args:
        prompt: The message/query to send to the Lucifex Agent.
        session_id: Optional session identifier to maintain conversation history.
    """
    try:
        agent = get_or_create_agent(session_id)
        logger.info(f"Running conversation turn for session {session_id or 'default'}")
        result = agent.run_conversation(prompt)
        response_text = result.get("final_response", "")
        if not response_text:
            return "No response from Lucifex."
        return response_text
    except Exception as e:
        logger.exception("Failed to run conversation on Lucifex agent")
        return f"Error communicating with Lucifex agent: {str(e)}"

@mcp.tool()
def run_command(command: str) -> str:
    """Execute a Lucifex CLI command and return its output.
    
    Use this to check status, list tools, view logs, or inspect the state of the agent.
    
    Args:
        command: The full command line to run, e.g., "lucifex status" or "lucifex tools".
    """
    import subprocess
    import shlex
    try:
        args = shlex.split(command)
        if not args:
            return "Error: Empty command string."
        
        # If command starts with "lucifex", map to python executable and cli.py
        if args[0] == "lucifex":
            args = [sys.executable, str(workspace_root / "cli.py")] + args[1:]
        elif args[0] == "python" and len(args) > 1 and args[1] == "cli.py":
            args = [sys.executable, str(workspace_root / "cli.py")] + args[2:]
            
        logger.info(f"Executing command: {args}")
        result = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
            cwd=str(workspace_root)
        )
        
        output = result.stdout or ""
        if result.stderr:
            output += f"\n--- Stderr Output ---\n{result.stderr}"
        return output
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 120 seconds."
    except Exception as e:
        logger.exception("Failed to run command")
        return f"Error executing command: {str(e)}"

@mcp.tool()
def get_lucifex_info() -> str:
    """Get status, environment configuration, and active profile information for Lucifex.
    
    Returns a JSON string containing current home directory, database configuration,
    and profile settings.
    """
    try:
        from lucifex_constants import get_lucifex_home, display_lucifex_home
        from lucifex_cli.config import load_config
        
        config = load_config()
        home = get_lucifex_home()
        
        info = {
            "lucifex_home": str(home),
            "display_home": display_lucifex_home(),
            "config_version": config.get("_config_version"),
            "model": config.get("model"),
            "provider": config.get("provider"),
            "enabled_toolsets": config.get("enabled_toolsets"),
            "active_profile": os.environ.get("LUCIFEX_PROFILE", "default")
        }
        return json.dumps(info, indent=2)
    except Exception as e:
        logger.exception("Failed to get info")
        return json.dumps({"error": f"Failed to retrieve info: {str(e)}"}, indent=2)

if __name__ == "__main__":
    import asyncio
    asyncio.run(mcp.run_stdio_async())
