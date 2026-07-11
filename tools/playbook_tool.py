#!/usr/bin/env python3
import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

def _resolve_obsidian_vault_path() -> Path:
    """Resolve o caminho absoluto do Obsidian Vault usando mcp_config.json ou fallback."""
    config_path = Path("C:/Users/gabri/.gemini/antigravity-ide/mcp_config.json")
    vault_path = None
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                vault_path = data.get("mcpServers", {}).get("obsidian", {}).get("env", {}).get("OBSIDIAN_VAULT_PATH")
        except Exception:
            pass
            
    if not vault_path:
        vault_path = "C:/Users/gabri/OneDrive/Documentos/Obsidian Vault"
        
    return Path(vault_path)

def sync_playbook() -> str:
    """Lê Discoveries e Decisions do Obsidian e compila o Engineering_Playbook.md."""
    vault = _resolve_obsidian_vault_path()
    if not vault.exists():
        return f"Error: Obsidian Vault not found at {vault}"
        
    discoveries_dir = vault / "Discoveries"
    decisions_dir = vault / "Decisions"
    
    entries = []
    
    # 1. Parse Discoveries (Descobertas)
    if discoveries_dir.exists():
        for file in discoveries_dir.glob("*.md"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    content = f.read()
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        import yaml
                        fm = yaml.safe_load(parts[1]) or {}
                        body = parts[2].strip()
                        entries.append({
                            "title": fm.get("title", file.stem),
                            "category": fm.get("category", "discovery"),
                            "tags": fm.get("tags", []),
                            "content": body,
                            "file": file.name,
                            "type": "Discovery"
                        })
            except Exception as e:
                logger.debug("Failed parsing discovery %s: %s", file.name, e)

    # 2. Parse Decisions (Decisões)
    if decisions_dir.exists():
        for file in decisions_dir.glob("*.md"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    content = f.read()
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        import yaml
                        fm = yaml.safe_load(parts[1]) or {}
                        body = parts[2].strip()
                        entries.append({
                            "title": fm.get("title", file.stem),
                            "category": "decision",
                            "tags": fm.get("tags", []),
                            "content": body,
                            "file": file.name,
                            "type": "Decision"
                        })
            except Exception as e:
                logger.debug("Failed parsing decision %s: %s", file.name, e)

    if not entries:
        return "No discoveries or decisions found to compile."

    # 3. Formatar o Playbook
    playbook_lines = [
        "# 📚 Lucifexia Engineering Playbook",
        "",
        "Este arquivo é compilado automaticamente a partir das descobertas e decisões do seu Obsidian Vault.",
        "Ele serve como referência para correções autônomas de falhas de ambiente e decisões de design.",
        "",
        "---",
        ""
    ]
    
    for entry in entries:
        tags_str = ", ".join(entry["tags"]) if entry["tags"] else "Nenhuma"
        playbook_lines.extend([
            f"## [{entry['type']}] {entry['title']}",
            f"- **Arquivo:** `{entry['file']}`",
            f"- **Categoria:** `{entry['category']}`",
            f"- **Tags:** `{tags_str}`",
            "",
            "### Resolução / Contexto:",
            entry["content"],
            "",
            "---",
            ""
        ])

    # 4. Gravar o Playbook no diretório home do Lucifex
    from lucifex_constants import get_lucifex_home
    playbook_path = Path(get_lucifex_home()) / "Engineering_Playbook.md"
    try:
        playbook_path.parent.mkdir(parents=True, exist_ok=True)
        with open(playbook_path, "w", encoding="utf-8") as f:
            f.write("\n".join(playbook_lines))
        return f"Playbook successfully compiled to {playbook_path} with {len(entries)} items."
    except Exception as e:
        return f"Error writing playbook: {str(e)}"

def get_playbook_tip(terminal_output: str) -> Optional[str]:
    """Busca correspondências no Playbook de acordo com o output de erro do terminal."""
    from lucifex_constants import get_lucifex_home
    playbook_path = Path(get_lucifex_home()) / "Engineering_Playbook.md"
    
    # Se não existir, tenta compilar na hora
    if not playbook_path.exists():
        sync_result = sync_playbook()
        logger.info("Auto-compiling playbook: %s", sync_result)
        
    if not playbook_path.exists():
        return None

    try:
        with open(playbook_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None

    # Dividir o playbook pelas divisórias de seções
    sections = content.split("\n---\n")
    matches = []
    
    # Palavras-chave extraídas da saída do terminal (limpa e normaliza)
    error_text = terminal_output.lower()
    
    for section in sections:
        if not section.strip() or "Lucifexia Engineering Playbook" in section:
            continue
            
        # Extrair dados de tags e termos da seção
        # Procurar se alguma tag ou o título ou o conteúdo da nota é mencionado no erro do terminal
        # Por exemplo, se na seção falar de "openpyxl" e a mensagem de erro do terminal contiver "openpyxl"
        section_lines = section.splitlines()
        title = ""
        tags = []
        
        for line in section_lines:
            if line.startswith("## "):
                title = line.replace("## ", "").strip()
            elif line.startswith("- **Tags:**"):
                tags_part = line.replace("- **Tags:**", "").strip()
                tags = [t.strip().lower() for t in tags_part.split(",") if t.strip()]

        # Procurar correspondências
        matched = False
        
        # 1. Se alguma tag da nota bater com o erro
        for tag in tags:
            if tag and tag in error_text:
                matched = True
                break
                
        # 2. Se palavras-chave do título ou termos específicos estiverem no erro
        # Ex: "ModuleNotFoundError" ou "openpyxl" ou nomes de arquivos
        if not matched:
            title_clean = title.lower()
            # Procurar termos principais do título
            for word in ["openpyxl", "excel", "sqlite", "import", "module"]:
                if word in title_clean and word in error_text:
                    matched = True
                    break
                    
        # 3. Busca direta de substrings relevantes
        if not matched:
            # Se a mensagem de erro do terminal contiver referências explícitas à solução
            # (busca básica simples de termos de erro específicos)
            if "modulenotfounderror" in error_text and "openpyxl" in error_text and "openpyxl" in section.lower():
                matched = True

        if matched:
            # Encontrou! Limpa e formata a dica da seção
            # Pega o corpo de contexto e solução da seção
            lines_to_return = []
            capture = False
            for line in section_lines:
                if line.startswith("### Resolução / Contexto:"):
                    capture = True
                    continue
                if capture:
                    lines_to_return.append(line)
            
            solution_body = "\n".join(lines_to_return).strip()
            matches.append(
                f"📌 **{title}**\n"
                f"{solution_body}"
            )
            
    if matches:
        # Retorna a dica combinada de todas as seções que bateram
        return "\n\n".join(matches)
        
    return None


from tools.registry import registry

playbook_sync_schema = {
    "name": "playbook_sync",
    "description": "Synchronize and compile the Lucifexia Engineering Playbook by reading Discoveries and Decisions from the Obsidian Vault.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

def playbook_sync_handler() -> str:
    """Ferramenta para sincronizar o playbook a partir do Obsidian."""
    return sync_playbook()

registry.register(
    name="playbook_sync",
    toolset="skills",
    schema=playbook_sync_schema,
    handler=playbook_sync_handler,
    description="Synchronize and compile the Lucifexia Engineering Playbook by reading Discoveries and Decisions from the Obsidian Vault.",
    emoji="📚"
)
