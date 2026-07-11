import os
import re
from pathlib import Path

root = Path(r"c:\Users\gabri\.gemini\antigravity-ide\scratch\lucifex-agent")
tools = []

for py_file in root.rglob("*.py"):
    if "tools" in py_file.parts or "agent" in py_file.parts:
        try:
            content = py_file.read_text(encoding="utf-8")
            for match in re.finditer(r"registry\.register\(\s*name\s*=\s*['\"](\w+)['\"]", content):
                tools.append((match.group(1), py_file.name))
        except Exception:
            pass

for t, f in sorted(list(set(tools))):
    print(f"Tool: {t:<30} (defined in {f})")
