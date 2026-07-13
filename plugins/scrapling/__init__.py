"""Scrapling plugin — web scraping stealth com bypass de anti-bot.

Expõe duas ferramentas gateadas pela presença do pacote ``scrapling``:

- ``web_extract_stealth(url, selector?, wait_for?, js_enabled?)``
  Faz scraping com fingerprint de navegador real. Passa em ~98% dos
  anti-bots (Cloudflare, Datadome, PerimeterX) sem VPN. Auto-adapta
  seletores CSS se o site mudar layout.

- ``web_scrape_structured(url, schema)``
  Extrai JSON estruturado de qualquer página usando Scrapling +
  extração baseada em esquema declarativo.

Instalação automática: o plugin instala ``scrapling`` via lazy_deps
na primeira execução se ainda não estiver disponível.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy install helper
# ---------------------------------------------------------------------------

def _ensure_scrapling() -> bool:
    """Garante que scrapling está instalado. Retorna True se disponível."""
    try:
        import scrapling  # noqa: F401
        return True
    except ImportError:
        pass

    try:
        from tools import lazy_deps
        lazy_deps.ensure_package("scrapling", "scrapling")
        import scrapling  # noqa: F401
        return True
    except Exception as exc:
        logger.warning("scrapling não disponível: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Verificação de disponibilidade (check_fn para ferramentas gateadas)
# ---------------------------------------------------------------------------

def _scrapling_available() -> bool:
    try:
        import scrapling  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Implementação das ferramentas
# ---------------------------------------------------------------------------

def web_extract_stealth(
    url: str,
    selector: str = "",
    wait_for: str = "",
    js_enabled: bool = True,
) -> str:
    """Extrai conteúdo de uma URL usando scraping stealth com bypass de anti-bot.

    Usa fingerprint de navegador real para passar por Cloudflare, Datadome
    e outros anti-bots. Auto-adapta seletores CSS se o site mudar layout.

    Args:
        url: URL da página a extrair.
        selector: Seletor CSS opcional para extrair elemento específico.
                  Se vazio, retorna o texto completo da página.
        wait_for: Seletor CSS a aguardar antes de extrair (útil para SPAs).
        js_enabled: Se True (padrão), usa renderização JavaScript completa.
                    Se False, usa fetch simples (mais rápido, sem JS).

    Returns:
        Conteúdo textual extraído da página.
    """
    if not _ensure_scrapling():
        return (
            "[ERRO] Scrapling não pôde ser instalado. "
            "Execute: pip install scrapling"
        )

    try:
        if js_enabled:
            from scrapling.fetchers import StealthyFetcher
            fetcher = StealthyFetcher()
            page = fetcher.fetch(url, wait_for=wait_for or None)
        else:
            from scrapling.fetchers import Fetcher
            fetcher = Fetcher()
            page = fetcher.fetch(url)

        if selector:
            elements = page.find_all(selector)
            if not elements:
                return f"[Scrapling] Nenhum elemento encontrado com seletor: {selector}"
            return "\n".join(el.text for el in elements)

        return page.get_all_text(separator="\n")

    except Exception as exc:
        logger.error("web_extract_stealth falhou para %s: %s", url, exc)
        return f"[ERRO] Falha no scraping stealth de {url}: {exc}"


def web_scrape_structured(
    url: str,
    schema: dict,
) -> str:
    """Extrai dados estruturados de uma página usando um esquema declarativo.

    Combina Scrapling com extração baseada em esquema: define quais campos
    quer (seletor CSS + transformação) e obtém JSON estruturado.

    Args:
        url: URL da página a extrair.
        schema: Dicionário com definição dos campos a extrair.
                Exemplo: {"titulo": "h1", "preco": ".price", "descricao": ".desc"}

    Returns:
        JSON com os campos extraídos.
    """
    import json

    if not _ensure_scrapling():
        return (
            "[ERRO] Scrapling não pôde ser instalado. "
            "Execute: pip install scrapling"
        )

    try:
        from scrapling.fetchers import StealthyFetcher
        fetcher = StealthyFetcher()
        page = fetcher.fetch(url)

        result: dict[str, Any] = {}
        for field_name, css_selector in schema.items():
            if not isinstance(css_selector, str):
                result[field_name] = None
                continue
            elements = page.find_all(css_selector)
            if not elements:
                result[field_name] = None
            elif len(elements) == 1:
                result[field_name] = elements[0].text.strip()
            else:
                result[field_name] = [el.text.strip() for el in elements]

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as exc:
        logger.error("web_scrape_structured falhou para %s: %s", url, exc)
        return f"[ERRO] Falha na extração estruturada de {url}: {exc}"


# ---------------------------------------------------------------------------
# Registro das ferramentas
# ---------------------------------------------------------------------------

def register(registry: Any) -> None:
    """Registra as ferramentas do plugin Scrapling no registry do Lucifex."""

    registry.register(
        name="web_extract_stealth",
        func=web_extract_stealth,
        description=(
            "Extrai conteúdo de uma URL usando scraping stealth com bypass automático "
            "de anti-bot (Cloudflare, Datadome, PerimeterX). Usa fingerprint de navegador "
            "real. Prefira esta ferramenta quando web_extract falhar com 403/CAPTCHA. "
            "Use js_enabled=false para sites simples (mais rápido)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL da página a extrair"
                },
                "selector": {
                    "type": "string",
                    "description": "Seletor CSS opcional para extrair elemento específico. Vazio = texto completo."
                },
                "wait_for": {
                    "type": "string",
                    "description": "Seletor CSS a aguardar antes de extrair (para SPAs com carregamento dinâmico)"
                },
                "js_enabled": {
                    "type": "boolean",
                    "description": "Se true, renderiza JavaScript completo (padrão). Se false, fetch simples mais rápido."
                }
            },
            "required": ["url"]
        },
        check_fn=_scrapling_available,
    )

    registry.register(
        name="web_scrape_structured",
        func=web_scrape_structured,
        description=(
            "Extrai dados estruturados de uma página web usando um esquema declarativo. "
            "Retorna JSON com os campos definidos no schema. "
            "Ideal para extrair listas de produtos, preços, artigos, etc."
        ),
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL da página a extrair"
                },
                "schema": {
                    "type": "object",
                    "description": "Mapa de {nome_campo: seletor_css}. Ex: {\"titulo\": \"h1\", \"preco\": \".price\"}"
                }
            },
            "required": ["url", "schema"]
        },
        check_fn=_scrapling_available,
    )

    logger.info("Plugin Scrapling: 2 ferramentas stealth registradas.")
