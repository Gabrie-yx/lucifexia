#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path
workspace_root = Path(__file__).parent.parent.absolute()
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from lucifex_cli.config import load_config
from lucifex_cli.runtime_provider import resolve_runtime_provider
from run_agent import AIAgent

def chat():
    print("Initializing Lucifex AIAgent locally...")
    cfg = load_config()
    
    # Resolve model and provider
    model_cfg = cfg.get("model") or {}
    if isinstance(model_cfg, str):
        cfg_model = model_cfg
    else:
        cfg_model = model_cfg.get("default") or model_cfg.get("model") or ""
        
    env_model = os.getenv("LUCIFEX_INFERENCE_MODEL", "").strip()
    effective_model = env_model or cfg_model
    
    cfg_provider = ""
    if isinstance(model_cfg, dict):
        cfg_provider = str(model_cfg.get("provider") or "").strip().lower()
    current_provider = (
        cfg_provider
        or os.getenv("LUCIFEX_INFERENCE_PROVIDER", "").strip().lower()
        or "auto"
    )
    
    runtime = resolve_runtime_provider(
        requested=current_provider,
        target_model=effective_model or None,
    )
    
    # Build the AIAgent instance
    agent = AIAgent(
        session_id="dev-chat-session",
        api_key=runtime.get("api_key"),
        base_url=runtime.get("base_url"),
        provider=runtime.get("provider"),
        api_mode=runtime.get("api_mode"),
        model=effective_model,
        credential_pool=runtime.get("credential_pool"),
        save_trajectories=False,
    )
    
    # Pergunta detalhada sobre as capacidades atuais do Lucifex
    prompt = (
        "Me dê uma lista detalhada de TODAS as suas capacidades, ferramentas nativas, "
        "plugins (como cron, spotify, kanban, etc.) e MCPs que você tem atualmente ativados, "
        "e o que você consegue fazer com eles. Preciso disso para mapear novas ideias "
        "de diferenciais que você ainda não possui."
    )
    
    print(f"Sending prompt to Lucifex ({effective_model} via {runtime.get('provider')})...")
    print("Please wait (local inference might take a few seconds)...")
    
    try:
        result = agent.run_conversation(prompt)
        response_text = result.get("final_response", "")
        print("\n=== RESPONSE FROM LUCIFEX ===")
        print(response_text)
        print("=============================")
    except Exception as e:
        print(f"Error chatting with Lucifex agent: {e}")

if __name__ == "__main__":
    chat()
