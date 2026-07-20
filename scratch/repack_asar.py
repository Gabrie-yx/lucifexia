import os
import shutil
import subprocess

def main():
    temp_dir = r"C:\Users\gabri\AppData\Local\Temp\new_asar_dir"
    workspace_dir = r"c:\Users\gabri\.gemini\antigravity-ide\scratch\lucifex-agent"
    
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    
    # Folders to copy
    folders = ["dist", "electron", "assets", "public"]
    for folder in folders:
        src = os.path.join(workspace_dir, "apps", "desktop", folder)
        dst = os.path.join(temp_dir, folder)
        if os.path.exists(src):
            print(f"Copying {src} to {dst}")
            shutil.copytree(src, dst)
            
    # Copy package.json
    shutil.copy2(
        os.path.join(workspace_dir, "apps", "desktop", "package.json"),
        os.path.join(temp_dir, "package.json")
    )
    
    # Run asar pack
    dest_asar = r"C:\Users\gabri\AppData\Local\Temp\app.asar"
    print(f"Packing {temp_dir} into {dest_asar}")
    subprocess.run(["npx", "asar", "pack", temp_dir, dest_asar], shell=True, check=True)
    print("Done packing!")

if __name__ == "__main__":
    main()
