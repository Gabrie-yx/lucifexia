import re

pattern = re.compile(r'hermes', re.IGNORECASE)

with open(r'c:\Users\gabri\.gemini\antigravity-ide\scratch\lucifex-agent\scripts\install.sh', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if pattern.search(line):
            print(f"Line {i+1}: {line.strip()}")
