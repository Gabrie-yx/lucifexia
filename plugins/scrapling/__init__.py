"""Scrapling plugin — web scraping stealth com bypass de anti-bot.

Expõe duas ferramentas de scraping:

- ``web_extract_stealth(url, selector?, wait_for?, js_enabled?)``
  Extrai conteúdo com fingerprint de browser real. Auto-adapta seletores.
  Usa renderização JS completa quando playwright estiver disponível.

- ``web_scrape_structured(url, schema)``
  Extrai JSON estruturado usando esquema declarativo de seletores CSS.

Instalação automática: instala ``scrapling`` via pip na primeira execução.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pip install helper — NÃO usa tools.lazy_deps (inacessível em plugins)
# ---------------------------------------------------------------------------

def _pip_install(package: str) -> bool:
    """Instala um pacote via pip. Retorna True em caso de sucesso."""
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", package, "--quiet",
             "--disable-pip-version-check"],
            timeout=120,
        )
        return True
    except Exception as exc:
        logger.warning("pip install %s falhou: %s", package, exc)
        return False


def _ensure_scrapling() -> bool:
    """Garante que scrapling está instalado. Instala se necessário."""
    try:
        import scrapling  # noqa: F401
        return True
    except ImportError:
        pass
    logger.info("Scrapling não encontrado — instalando...")
    if _pip_install("scrapling"):
        try:
            import scrapling  # noqa: F401
            return True
        except ImportError:
            pass
    return False


def _scrapling_available() -> bool:
    try:
        import scrapling  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Fetcher factory — usa JS rendering quando playwright disponível,
# fallback para Fetcher httpx (sem browser) caso contrário.
# ---------------------------------------------------------------------------

def _make_fetcher(js_enabled: bool, wait_for: str = ""):
    """Retorna o melhor fetcher disponível dado o contexto."""
    import scrapling
    from scrapling.fetchers import Fetcher

    if not js_enabled:
        return Fetcher(auto_match=True), "httpx"

    # Tenta PlaywrightFetcher (scrapling ≥ 0.2)
    try:
        from scrapling.fetchers import PlaywrightFetcher
        return PlaywrightFetcher(auto_match=True, headless=True), "playwright"
    except (ImportError, AttributeError):
        pass

    # Tenta StealthyFetcher (scrapling < 0.2)
    try:
        from scrapling.fetchers import StealthyFetcher
        return StealthyFetcher(auto_match=True), "stealth"
    except (ImportError, AttributeError):
        pass

    # Último recurso: Fetcher simples
    return Fetcher(auto_match=True), "httpx-fallback"


def _page_text(page) -> str:
    """Extrai texto de uma página Scrapling de forma compatível entre versões."""
    # scrapling 0.2+: get_all_text()
    if hasattr(page, "get_all_text"):
        return page.get_all_text(separator="\n")
    # Fallback: html attribute
    if hasattr(page, "html"):
        html = page.html or ""
        # Remove tags simples para retornar texto limpo
        import re
        return re.sub(r"<[^>]+>", " ", html).strip()
    return str(page)


# ---------------------------------------------------------------------------
# Implementação das ferramentas
# ---------------------------------------------------------------------------

def web_extract_stealth(
    url: str,
    selector: str = "",
    wait_for: str = "",
    js_enabled: bool = True,
) -> str:
    """Extrai conteúdo de uma URL usando scraping com bypass de anti-bot.

    Usa fingerprint de browser real. Tenta renderização JavaScript quando
    playwright está instalado; usa httpx rápido como fallback.
    Auto-adapta seletores CSS se o site mudar layout.

    Args:
        url: URL da página a extrair.
        selector: Seletor CSS opcional para elemento específico.
                  Vazio = texto completo da página.
        wait_for: Seletor CSS a aguardar (para SPAs com carregamento dinâmico).
        js_enabled: True = renderização JS completa (quando disponível).
                    False = fetch httpx rápido (sem JavaScript).

    Returns:
        Conteúdo textual extraído da página.
    """
    if not _ensure_scrapling():
        return (
            "❌ Scrapling não pôde ser instalado.\n"
            "Execute manualmente: pip install scrapling\n"
            "Depois tente novamente."
        )

    try:
        fetcher, engine = _make_fetcher(js_enabled, wait_for)
        logger.debug("web_extract_stealth: usando engine=%s para %s", engine, url)

        # Busca a página
        try:
            if js_enabled and wait_for and engine != "httpx-fallback":
                page = fetcher.fetch(url, wait_for=wait_for)
            else:
                page = fetcher.fetch(url)
        except TypeError:
            # Alguns fetchers não aceitam wait_for
            page = fetcher.fetch(url)

        if selector:
            try:
                elements = page.find_all(selector)
            except AttributeError:
                # API alternativa
                elements = page.css(selector) if hasattr(page, "css") else []
            if not elements:
                return f"[Scrapling/{engine}] Nenhum elemento encontrado com seletor: {selector}"
            return "\n".join(
                getattr(el, "text", str(el)).strip() for el in elements
            )

        return _page_text(page)

    except Exception as exc:
        logger.error("web_extract_stealth falhou para %s: %s", url, exc)
        return f"[ERRO] Falha no scraping de {url}: {exc}"


def web_scrape_structured(
    url: str,
    schema: dict,
) -> str:
    """Extrai dados estruturados de uma página usando esquema declarativo CSS.

    Args:
        url: URL da página a extrair.
        schema: Dicionário {nome_campo: seletor_css}.
                Exemplo: {"titulo": "h1", "preco": ".price", "descricao": ".desc"}

    Returns:
        JSON com os campos extraídos conforme o schema.
    """
    import json

    if not _ensure_scrapling():
        return (
            "❌ Scrapling não pôde ser instalado.\n"
            "Execute manualmente: pip install scrapling"
        )

    if not isinstance(schema, dict) or not schema:
        return "[ERRO] schema deve ser um dicionário {campo: seletor_css} não-vazio."

    try:
        fetcher, engine = _make_fetcher(js_enabled=False)
        logger.debug("web_scrape_structured: engine=%s para %s", engine, url)
        page = fetcher.fetch(url)

        result: dict[str, Any] = {}
        for field_name, css_selector in schema.items():
            if not isinstance(css_selector, str):
                result[field_name] = None
                continue
            try:
                elements = page.find_all(css_selector)
            except AttributeError:
                elements = page.css(css_selector) if hasattr(page, "css") else []

            if not elements:
                result[field_name] = None
            elif len(elements) == 1:
                result[field_name] = getattr(elements[0], "text", str(elements[0])).strip()
            else:
                result[field_name] = [
                    getattr(el, "text", str(el)).strip() for el in elements
                ]

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as exc:
        logger.error("web_scrape_structured falhou para %s: %s", url, exc)
        return f"[ERRO] Falha na extração estruturada de {url}: {exc}"


# ---------------------------------------------------------------------------
# Registro das ferramentas — SEM check_fn para que apareçam sempre.
# A instalação acontece na primeira chamada via _ensure_scrapling().
# ---------------------------------------------------------------------------

def register(registry: Any) -> None:
    """Registra as ferramentas do plugin Scrapling."""

    registry.register(
        name="web_extract_stealth",
        func=web_extract_stealth,
        description=(
            "Extrai conteúdo de uma URL com bypass automático de anti-bot "
            "(Cloudflare, Datadome, PerimeterX). Usa fingerprint de browser real "
            "e auto-adapta seletores CSS quando o site muda layout. "
            "Prefira esta ferramenta quando web_extract falhar com 403/CAPTCHA. "
            "Use js_enabled=false para sites simples (mais rápido, sem JS)."
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
                    "description": "Seletor CSS opcional. Vazio = texto completo da página."
                },
                "wait_for": {
                    "type": "string",
                    "description": "Seletor CSS a aguardar (para SPAs com carregamento dinâmico)"
                },
                "js_enabled": {
                    "type": "boolean",
                    "description": "true = renderiza JavaScript (padrão). false = fetch rápido sem JS."
                }
            },
            "required": ["url"]
        },
    )

    registry.register(
        name="web_scrape_structured",
        func=web_scrape_structured,
        description=(
            "Extrai dados estruturados de uma página web usando esquema declarativo CSS. "
            "Retorna JSON com os campos definidos no schema. "
            "Ideal para extrair listas de produtos, preços, artigos, tabelas, etc."
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
                    "description": (
                        'Mapa de {nome_campo: seletor_css}. '
                        'Exemplo: {"titulo": "h1", "preco": ".price", "descricao": ".desc"}'
                    )
                }
            },
            "required": ["url", "schema"]
        },
    )

    logger.info("Plugin Scrapling: 2 ferramentas registradas (web_extract_stealth, web_scrape_structured).")
