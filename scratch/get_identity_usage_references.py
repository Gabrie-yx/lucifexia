from pathlib import Path

py_file = Path(r"c:\Users\gabri\.gemini\antigravity-ide\scratch\lucifex-agent\run_agent.py")
target = "DEFAULT_AGENT_IDENTITY"
content = py_file.read_text(encoding="utf-8")
lines = content.splitlines()

for idx, line in enumerate(lines):
    if target in line and idx != 159: # skip the import
        print(f"Line {idx+1}: {line.strip()}")
        start = max(0, idx - 5)
        end = min(len(lines), idx + 6)
        for i in range(start, end):
            prefix = "--> " if i == idx else "    "
            print(f"{prefix}{i+1}: {lines[i]}")
