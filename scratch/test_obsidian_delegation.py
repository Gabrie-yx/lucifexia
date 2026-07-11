#!/usr/bin/env python3
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
workspace_root = Path(__file__).parent.parent.absolute()
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from tools.delegate_tool import _build_child_agent, _load_obsidian_agent_profile

class DummyParentAgent:
    def __init__(self):
        self.model = "lucifexia:v2"
        self.provider = "ollama"
        self.base_url = "http://127.0.0.1:11434/v1"
        self.api_key = "dummy_key"
        self.api_mode = "chat_completions"
        self.valid_tool_names = ["terminal", "read_file"]
        self.enabled_toolsets = ["terminal"]
        self._delegate_depth = 0

def test_delegation():
    print("Testing Obsidian Agent Co-Processor...")
    
    # 1. Testar o carregamento da persona
    print("\n1. Testing _load_obsidian_agent_profile for 'tony-stark-orchestrator'...")
    profile = _load_obsidian_agent_profile("tony-stark-orchestrator")
    if not profile:
        print("FAIL: Could not load profile. Ensure Obsidian Vault path is correct in mcp_config.json")
        return
        
    print("SUCCESS: Loaded Obsidian profile!")
    fm = profile["frontmatter"]
    print(f"Agent Name: {fm.get('name')}")
    print(f"Agent Role: {fm.get('role')}")
    print(f"Agent Model (frontmatter): {fm.get('model')}")
    
    # 2. Testar a construção do subagente
    print("\n2. Testing _build_child_agent with role='tony-stark-orchestrator'...")
    parent = DummyParentAgent()
    child = _build_child_agent(
        task_index=0,
        goal="Analisar latência de banco de dados do SQLite",
        context="Tabela sessions com FTS5",
        toolsets=None,
        model=None,
        max_iterations=50,
        task_count=1,
        parent_agent=parent,
        role="tony-stark-orchestrator"
    )
    
    print("SUCCESS: Built child agent!")
    print(f"Child Model resolved: {child.model}")
    print(f"Child Role resolved: {getattr(child, '_delegate_role', 'Not set')}")
    
    # 3. Inspecionar System Prompt
    system_prompt = child.ephemeral_system_prompt
    print("\n3. Inspecting Child System Prompt:")
    print("-" * 60)
    # Print the first 15 lines of the system prompt to verify injection
    prompt_lines = system_prompt.splitlines()
    for line in prompt_lines[:15]:
        print(line)
    print("...")
    print("-" * 60)
    
    if "Tony Stark" in system_prompt and "CORE IDENTITY & PERSONALITY MATRIX" in system_prompt:
        print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
    else:
        print("\n❌ TEST FAILED: Obsidian agent persona was not injected into system prompt.")

if __name__ == "__main__":
    test_delegation()
