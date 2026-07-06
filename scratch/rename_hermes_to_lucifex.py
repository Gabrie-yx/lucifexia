import os

replacements = [
    # Order from most specific to least specific
    ("HERMES_HOME", "LUCIFEX_HOME"),
    ("HermesHome", "LucifexHome"),
    ("hermes-agent", "lucifex-agent"),
    ("hermes-setup", "lucifex-setup"),
    ("Hermes-Setup", "Lucifex-Setup"),
    ("hermes_cli", "lucifex_cli"),
    ("com.nousresearch.hermes", "com.nousresearch.lucifex"),
    ("com.nousresearch.LUCIFEX", "com.nousresearch.lucifex"),
    ("com.lucifex.agent", "com.nousresearch.lucifex"),
    ("Hermes", "Lucifex"),
    ("hermes", "lucifex"),
]

files_to_update = [
    r"c:\Users\gabri\.gemini\antigravity-ide\scratch\lucifex-agent\scripts\install.ps1",
    r"c:\Users\gabri\.gemini\antigravity-ide\scratch\lucifex-agent\scripts\install.sh",
    r"c:\Users\gabri\.gemini\antigravity-ide\scratch\lucifex-agent\scripts\lib\node-bootstrap.sh",
    r"c:\Users\gabri\.gemini\antigravity-ide\scratch\lucifex-agent\setup-lucifex.sh",
    r"c:\Users\gabri\.gemini\antigravity-ide\scratch\lucifex-agent\scripts\install.cmd",
]

for filepath in files_to_update:
    if not os.path.exists(filepath):
        print(f"Skipping nonexistent: {filepath}")
        continue
    
    print(f"Updating {filepath}...")
    try:
        # Detect encoding
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
            print(f"  Successfully updated {filepath} using {encoding} encoding.")
        else:
            print(f"  No changes needed for {filepath}.")
            
    except Exception as e:
        print(f"  Error updating {filepath}: {e}")
