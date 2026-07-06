import os

replacements = [
    ("HERMES_INSTALL_DIR", "LUCIFEX_INSTALL_DIR"),
    ("HERMES_BIN", "LUCIFEX_BIN"),
    ("HERMES_CMD", "LUCIFEX_CMD"),
]

filepath = r"c:\Users\gabri\.gemini\antigravity-ide\scratch\lucifex-agent\scripts\install.sh"
try:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    original_content = content
    for src, dest in replacements:
        content = content.replace(src, dest)
        
    if content != original_content:
        with open(filepath, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        print("Updated install.sh variables.")
except Exception as e:
    print(f"Error: {e}")
