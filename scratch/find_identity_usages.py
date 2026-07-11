import os
from pathlib import Path

root = Path(r"c:\Users\gabri\.gemini\antigravity-ide\scratch\lucifex-agent")
target = "DEFAULT_AGENT_IDENTITY"

for py_file in root.rglob("*.py"):
    try:
        content = py_file.read_text(encoding="utf-8")
        if target in content and py_file.name != "prompt_builder.py":
            print(f"Found in: {py_file.relative_to(root)}")
            # Show the context
            lines = content.splitlines()
            for idx, line in enumerate(lines):
                if target in line:
                    print(f"  Line {idx+1}: {line.strip()}")
    except Exception as e:
        pass
