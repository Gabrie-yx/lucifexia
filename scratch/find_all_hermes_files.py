import os
import re

pattern = re.compile(r'hermes', re.IGNORECASE)
exclude_dirs = {'.git', 'node_modules', 'build', 'release', 'dist', '.agents', '.gemini'}

matches = []
for root, dirs, files in os.walk(r'c:\Users\gabri\.gemini\antigravity-ide\scratch\lucifex-agent'):
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    for file in files:
        # Skip binary files or specific extensions if needed
        if file.endswith(('.png', '.ico', '.jpg', '.pdf', '.woff2', '.ttf', '.pyc', '.zip')):
            continue
        path = os.path.join(root, file)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                if pattern.search(content):
                    matches.append(path)
        except Exception:
            pass

for m in matches:
    print(m)
