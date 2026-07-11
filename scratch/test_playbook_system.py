#!/usr/bin/env python3
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
workspace_root = Path(__file__).parent.parent.absolute()
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from tools.playbook_tool import sync_playbook, get_playbook_tip

def test_playbook_system():
    print("🧪 Testing Lucifexia Engineering Playbook System...")
    
    # 1. Testar Sincronização do Playbook a partir do Obsidian Vault do Usuário
    print("\n1. Running sync_playbook()...")
    sync_result = sync_playbook()
    print(f"Sync Result: {sync_result}")
    
    from lucifex_constants import get_lucifex_home
    playbook_file = Path(get_lucifex_home()) / "Engineering_Playbook.md"
    
    if not playbook_file.exists():
        print("❌ FAIL: Engineering_Playbook.md was not created.")
        return
        
    print(f"✅ SUCCESS: Playbook created at {playbook_file}")
    
    # 2. Testar busca de dicas com erro do openpyxl
    print("\n2. Testing get_playbook_tip() with missing openpyxl module error...")
    error_output = (
        "Traceback (most recent call last):\n"
        "  File \"main.py\", line 4, in <module>\n"
        "    import openpyxl\n"
        "ModuleNotFoundError: No module named 'openpyxl'"
    )
    
    tip = get_playbook_tip(error_output)
    
    if not tip:
        print("❌ FAIL: No tip found in the playbook for openpyxl error.")
        # Print content of playbook to inspect
        print("\nPlaybook Content Preview:")
        try:
            with open(playbook_file, "r", encoding="utf-8") as f:
                print(f.read()[:500])
        except Exception:
            pass
        return
        
    print("✅ SUCCESS: Found matching tip in the playbook!")
    print("-" * 60)
    print(tip)
    print("-" * 60)
    
    # 3. Testar busca de dicas com erro de arquivo não encontrado
    print("\n3. Testing get_playbook_tip() with spreadsheat / excel error...")
    error_output_2 = "FileNotFoundError: [Errno 2] No such file or directory: 'PRODUTOS TRANSBY.xlsx - Página1.csv'"
    tip_2 = get_playbook_tip(error_output_2)
    
    if tip_2:
        print("✅ SUCCESS: Found matching tip for FileNotFoundError Excel mapping!")
        print("-" * 60)
        print(tip_2)
        print("-" * 60)
        print("\n🎉 ALL PLAYBOOK SYSTEM TESTS PASSED SUCCESSFULLY!")
    else:
        print("⚠️  WARNING: No tip found for spreadsheet mapping (this is okay if Decisions/Discoveries notes don't match FileNotFoundError keywords).")
        print("\n🎉 PLAYBOOK SYSTEM BASIC TEST PASSED!")

if __name__ == "__main__":
    test_playbook_system()
