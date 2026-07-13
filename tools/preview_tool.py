"""Preview Tool — permite ao agente comandar a abertura do painel de Preview no Desktop.

Expõe a ferramenta ``open_preview(path_or_url)``.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from tools.registry import registry
from tools.file_tools import _resolve_path

logger = logging.getLogger(__name__)


def open_preview(path_or_url: str, task_id: Optional[str] = None) -> str:
    """Abre um arquivo local ou URL web no painel de Preview do Lucifex Desktop.

    Args:
        path_or_url: URL web (http/https) ou caminho do arquivo local (ex: 'index.html').
        task_id: Identificador da tarefa (resolução de caminhos).

    Returns:
        Mensagem de sucesso a ser exibida no log do agente.
    """
    path_or_url = path_or_url.strip()
    if path_or_url.startswith(("http://", "https://", "file://")):
        logger.info("open_preview: abrindo URL no painel de Preview: %s", path_or_url)
        return f"✅ Solicitada a abertura da URL no painel de Preview: {path_or_url}"

    # Resolve caminhos relativos ao workspace do usuário
    try:
        resolved = _resolve_path(path_or_url, task_id or "default")
        resolved_str = str(resolved).replace("\\", "/")
        logger.info("open_preview: abrindo arquivo local no painel de Preview: %s", resolved_str)
        return f"✅ Solicitada a abertura do arquivo local no painel de Preview: {resolved_str}"
    except Exception as exc:
        logger.warning("Falha ao resolver caminho para open_preview: %s", exc)
        return f"✅ Solicitada a abertura do arquivo no painel de Preview (caminho original): {path_or_url}"


# ---------------------------------------------------------------------------
# Registro da ferramenta
# ---------------------------------------------------------------------------

registry.register(
    name="open_preview",
    toolset="preview",
    schema={
        "name": "open_preview",
        "description": (
            "Abre um arquivo local (HTML, SVG, MD, imagens) ou uma URL da web "
            "diretamente no painel de Preview do Lucifex Desktop. "
            "Use esta ferramenta sempre que quiser forçar a exibição de um resultado "
            "visual ou página web na interface para o usuário."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path_or_url": {
                    "type": "string",
                    "description": "Caminho do arquivo local (ex: 'index.html', 'src/assets/logo.svg') ou URL web"
                }
            },
            "required": ["path_or_url"]
        }
    },
    handler=open_preview,
    emoji="🖥️",
)
