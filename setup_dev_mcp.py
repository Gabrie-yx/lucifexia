#!/usr/bin/env python3
"""
Setup script to automatically register Lucifex as an MCP server in the IDE agent's configuration.
Can be run by the user or by the Lucifex agent itself.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def setup():
    print("🚀 Starting Lucifex MCP developer setup...")

    # 1. Install mcp library
    print("📦 Installing required 'mcp' library...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "mcp"], check=True)
        print("✅ 'mcp' library installed successfully.")
    except Exception as e:
        print(f"⚠️ Failed to install 'mcp' automatically: {e}", file=sys.stderr)
        print("Please run: pip install mcp", file=sys.stderr)

    # 2. Paths detection
    home = Path.home()
    ide_config_dir = home / ".gemini" / "antigravity-ide"
    mcp_config_path = ide_config_dir / "mcp_config.json"
    
    script_path = Path(__file__).parent.absolute() / "lucifex_dev_mcp.py"
    
    if not script_path.exists():
        print(f"❌ Could not find 'lucifex_dev_mcp.py' at: {script_path}", file=sys.stderr)
        sys.exit(1)

    print(f"🔍 IDE Config directory: {ide_config_dir}")
    print(f"🔍 Script path to register: {script_path}")

    # Ensure IDE config dir exists
    if not ide_config_dir.exists():
        print("⚠️ Antigravity/Gemini IDE configuration directory not found. "
              "Please make sure the IDE is installed and has run at least once.")
        sys.exit(1)

    # 3. Read and modify configuration
    config = {"mcpServers": {}}
    if mcp_config_path.exists():
        try:
            with open(mcp_config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            print(f"⚠️ Error reading existing mcp_config.json: {e}", file=sys.stderr)
            print("Creating a new config layout...")

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    # Add or update the lucifex entry
    config["mcpServers"]["lucifex"] = {
        "command": sys.executable,  # Uses the active python interpreter
        "args": [str(script_path)]
    }

    try:
        with open(mcp_config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        print(f"🎉 Successfully registered Lucifex MCP server in: {mcp_config_path}")
        print("💡 Next Step: Reload your IDE or start a new chat session to activate it.")
    except Exception as e:
        print(f"❌ Failed to write config to {mcp_config_path}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    setup()
