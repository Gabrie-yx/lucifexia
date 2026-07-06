import os

replacements = [
    ("HERMES_GIT_BASH_PATH", "LUCIFEX_GIT_BASH_PATH"),
]

files_to_update = [
    r"c:\Users\gabri\.gemini\antigravity-ide\scratch\lucifex-agent\scripts\install.ps1",
    r"c:\Users\gabri\.gemini\antigravity-ide\scratch\lucifex-agent\scripts\install.sh",
    r"c:\Users\gabri\.gemini\antigravity-ide\scratch\lucifex-agent\scripts\lib\node-bootstrap.sh",
    r"c:\Users\gabri\.gemini\antigravity-ide\scratch\lucifex-agent\setup-lucifex.sh",
]

for filepath in files_to_update:
    if not os.path.exists(filepath):
        continue
    
    try:
        encoding = "utf-8"
        try:
            with open(filepath, "r", encoding="utf-16") as f:
                content = f.read()
                encoding = "utf-16"
        except UnicodeError:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                encoding = "utf-8"
        
        original_content = content
        for src, dest in replacements:
            content = content.replace(src, dest)
            
        if content != original_content:
            with open(filepath, "w", encoding=encoding, newline="") as f:
                f.write(content)
            print(f"Updated {filepath}")
    except Exception as e:
        print(f"Error: {e}")
