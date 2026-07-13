"""Agent-Reach plugin — leitura de redes sociais sem custo de API.

Expõe ferramentas que dão ao agente acesso a conteúdo de plataformas
sociais sem necessidade de chaves de API ou autenticação:

- ``social_read(platform, query_or_url)``
  Lê ou pesquisa em Twitter/X, Reddit, GitHub, XiaoHongShu, Bilibili.

- ``youtube_transcript(url, language?)``
  Baixa transcrição completa de um vídeo do YouTube.

- ``reddit_search(subreddit, query, limit?)``
  Pesquisa posts e comentários em um subreddit específico.

Instalação automática: instala ``agent-reach`` e ``youtube-transcript-api``
via lazy_deps na primeira execução.

Baseado em: https://github.com/Panniantong/agent-reach
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy install helpers
# ---------------------------------------------------------------------------

def _ensure_agent_reach() -> bool:
    """Garante que agent-reach está instalado."""
    try:
        import agent_reach  # noqa: F401
        return True
    except ImportError:
        pass
    try:
        from tools import lazy_deps
        lazy_deps.ensure_package("agent-reach", "agent_reach")
        import agent_reach  # noqa: F401
        return True
    except Exception as exc:
        logger.warning("agent-reach não disponível: %s", exc)
        return False


def _ensure_yt_transcript() -> bool:
    """Garante que youtube-transcript-api está instalado."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # noqa: F401
        return True
    except ImportError:
        pass
    try:
        from tools import lazy_deps
        lazy_deps.ensure_package("youtube-transcript-api", "youtube_transcript_api")
        from youtube_transcript_api import YouTubeTranscriptApi  # noqa: F401
        return True
    except Exception as exc:
        logger.warning("youtube-transcript-api não disponível: %s", exc)
        return False


def _agent_reach_available() -> bool:
    try:
        import agent_reach  # noqa: F401
        return True
    except ImportError:
        return False


def _yt_available() -> bool:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Implementação das ferramentas
# ---------------------------------------------------------------------------

_PLATFORM_HELP = (
    "Plataformas suportadas: twitter, reddit, github, xiaohongshu, bilibili. "
    "query_or_url pode ser uma URL direta ou um termo de pesquisa."
)

_SUPPORTED_PLATFORMS = {"twitter", "x", "reddit", "github", "xiaohongshu", "xhs", "bilibili"}


def social_read(
    platform: str,
    query_or_url: str,
    limit: int = 10,
) -> str:
    """Lê e pesquisa conteúdo de redes sociais sem precisar de chaves de API.

    Args:
        platform: Plataforma alvo. Suporta: twitter, reddit, github,
                  xiaohongshu, bilibili.
        query_or_url: URL direta de um post/perfil OU termo de pesquisa.
        limit: Número máximo de resultados (padrão: 10).

    Returns:
        Conteúdo encontrado em formato texto estruturado.
    """
    platform = platform.lower().strip()

    # Fallback: se agent_reach não estiver disponível, tenta via web scraping simples
    if not _ensure_agent_reach():
        return _social_read_fallback(platform, query_or_url, limit)

    try:
        import agent_reach as ar

        result = ar.fetch(platform=platform, query=query_or_url, limit=limit)
        if isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False, indent=2)
        return str(result)

    except AttributeError:
        # API do agent_reach pode ter estrutura diferente
        return _social_read_fallback(platform, query_or_url, limit)
    except Exception as exc:
        logger.error("social_read falhou para %s/%s: %s", platform, query_or_url, exc)
        return f"[ERRO] Falha ao acessar {platform}: {exc}"


def _social_read_fallback(platform: str, query_or_url: str, limit: int) -> str:
    """Fallback via requests simples para quando agent_reach não está disponível."""
    import urllib.request
    import urllib.parse

    platform = platform.lower()

    try:
        if platform in ("reddit",):
            if query_or_url.startswith("http"):
                url = query_or_url.rstrip("/") + ".json?limit=" + str(limit)
            else:
                url = f"https://www.reddit.com/search.json?q={urllib.parse.quote(query_or_url)}&limit={limit}"

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "lucifex-agent/1.0 (+https://lucifex.ai)"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            posts = data.get("data", {}).get("children", [])
            lines = []
            for p in posts[:limit]:
                d = p.get("data", {})
                lines.append(
                    f"📌 {d.get('title', '?')}\n"
                    f"   ↑{d.get('score', 0)} | r/{d.get('subreddit', '?')} | "
                    f"https://reddit.com{d.get('permalink', '')}"
                )
            return "\n\n".join(lines) if lines else "Nenhum resultado encontrado."

        elif platform in ("github",):
            if "github.com/" in query_or_url:
                return f"Use a ferramenta web_extract para ler {query_or_url} diretamente."
            url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query_or_url)}&per_page={limit}"
            req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            items = data.get("items", [])
            lines = [
                f"⭐ {r['full_name']} ({r.get('stargazers_count', 0)} ⭐)\n"
                f"   {r.get('description', '')}\n"
                f"   {r.get('html_url', '')}"
                for r in items[:limit]
            ]
            return "\n\n".join(lines) if lines else "Nenhum repositório encontrado."

        else:
            return (
                f"[Agent-Reach] Instale agent-reach para acessar {platform}: "
                f"pip install agent-reach\n\n"
                f"Plataformas com fallback: reddit, github.\n"
                f"Plataformas que precisam do agent-reach: twitter, xiaohongshu, bilibili."
            )

    except Exception as exc:
        return f"[ERRO] social_read fallback falhou: {exc}"


def youtube_transcript(
    url: str,
    language: str = "pt",
) -> str:
    """Baixa a transcrição completa de um vídeo do YouTube.

    Retorna o texto completo da transcrição, ideal para análise de conteúdo,
    resumos, extração de informações e citações sem assistir o vídeo.

    Args:
        url: URL do vídeo do YouTube (youtube.com/watch?v=... ou youtu.be/...).
        language: Código de idioma preferido (padrão: 'pt' para português).
                  Se não disponível, tenta 'en'. Se nenhum, retorna o primeiro.

    Returns:
        Transcrição completa do vídeo como texto contínuo.
    """
    if not _ensure_yt_transcript():
        return (
            "[ERRO] youtube-transcript-api não pôde ser instalado. "
            "Execute: pip install youtube-transcript-api"
        )

    try:
        import re
        from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound

        # Extrai o video_id da URL
        vid_match = re.search(r"(?:v=|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})", url)
        if not vid_match:
            return f"[ERRO] Não foi possível extrair o ID do vídeo de: {url}"

        video_id = vid_match.group(1)

        # Tenta o idioma preferido, depois inglês, depois qualquer um
        try_langs = [language, "en", "pt-BR", "pt-PT"]
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        transcript = None
        for lang in try_langs:
            try:
                transcript = transcript_list.find_transcript([lang])
                break
            except NoTranscriptFound:
                continue

        if transcript is None:
            # Pega o primeiro disponível
            available = list(transcript_list)
            if not available:
                return "[ERRO] Nenhuma transcrição disponível para este vídeo."
            transcript = available[0]

        segments = transcript.fetch()
        text = " ".join(seg.get("text", "") for seg in segments)

        lang_info = getattr(transcript, "language_code", "?")
        return f"[Transcrição YouTube | idioma: {lang_info} | {len(segments)} segmentos]\n\n{text}"

    except Exception as exc:
        logger.error("youtube_transcript falhou para %s: %s", url, exc)
        return f"[ERRO] Falha ao obter transcrição de {url}: {exc}"


def reddit_search(
    subreddit: str,
    query: str,
    limit: int = 15,
    sort: str = "relevance",
) -> str:
    """Pesquisa posts e comentários em um subreddit específico do Reddit.

    Não requer autenticação. Usa a API JSON pública do Reddit.

    Args:
        subreddit: Nome do subreddit (sem o prefixo r/). Ex: "LocalLLaMA"
        query: Termo de pesquisa.
        limit: Número máximo de resultados (padrão: 15, máximo: 100).
        sort: Ordenação. Opções: relevance, hot, top, new, comments.

    Returns:
        Lista de posts encontrados com título, score, URL e trecho do texto.
    """
    import urllib.request
    import urllib.parse

    try:
        limit = min(int(limit), 100)
        url = (
            f"https://www.reddit.com/r/{urllib.parse.quote(subreddit)}/search.json"
            f"?q={urllib.parse.quote(query)}&restrict_sr=1&sort={sort}&limit={limit}"
        )
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "lucifex-agent/1.0 (+https://lucifex.ai)"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        posts = data.get("data", {}).get("children", [])
        if not posts:
            return f"Nenhum post encontrado em r/{subreddit} para: {query}"

        lines = []
        for p in posts:
            d = p.get("data", {})
            title = d.get("title", "?")
            score = d.get("score", 0)
            permalink = d.get("permalink", "")
            selftext = (d.get("selftext", "") or "")[:300]
            num_comments = d.get("num_comments", 0)

            lines.append(
                f"📌 **{title}**\n"
                f"   ↑{score} pontos | 💬 {num_comments} comentários\n"
                f"   https://reddit.com{permalink}\n"
                + (f"   {selftext}..." if selftext else "")
            )

        return f"Resultados em r/{subreddit} para '{query}':\n\n" + "\n\n".join(lines)

    except Exception as exc:
        logger.error("reddit_search falhou para r/%s '%s': %s", subreddit, query, exc)
        return f"[ERRO] Falha ao pesquisar r/{subreddit}: {exc}"


# ---------------------------------------------------------------------------
# Registro das ferramentas
# ---------------------------------------------------------------------------

def register(registry: Any) -> None:
    """Registra as ferramentas do plugin Agent-Reach."""

    registry.register(
        name="social_read",
        func=social_read,
        description=(
            "Lê e pesquisa conteúdo de redes sociais sem precisar de chaves de API. "
            "Suporta Twitter/X, Reddit, GitHub, XiaoHongShu, Bilibili. "
            "Use para pesquisar opiniões, tendências, posts e perfis em redes sociais. "
            "query_or_url pode ser uma URL direta ou um termo de pesquisa."
        ),
        parameters={
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "description": "Plataforma: twitter, reddit, github, xiaohongshu, bilibili",
                    "enum": ["twitter", "reddit", "github", "xiaohongshu", "bilibili"]
                },
                "query_or_url": {
                    "type": "string",
                    "description": "URL direta de um post/perfil OU termo de pesquisa"
                },
                "limit": {
                    "type": "integer",
                    "description": "Número máximo de resultados (padrão: 10)",
                    "default": 10
                }
            },
            "required": ["platform", "query_or_url"]
        },
    )

    registry.register(
        name="youtube_transcript",
        func=youtube_transcript,
        description=(
            "Baixa a transcrição completa de um vídeo do YouTube sem precisar assistir. "
            "Ideal para análise de conteúdo, resumos e extração de informações. "
            "Suporta múltiplos idiomas com fallback automático para inglês."
        ),
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL do vídeo YouTube (youtube.com/watch?v=... ou youtu.be/...)"
                },
                "language": {
                    "type": "string",
                    "description": "Código de idioma preferido, ex: 'pt', 'en', 'es' (padrão: 'pt')",
                    "default": "pt"
                }
            },
            "required": ["url"]
        },
        check_fn=_yt_available,
    )

    registry.register(
        name="reddit_search",
        func=reddit_search,
        description=(
            "Pesquisa posts e comentários em um subreddit específico do Reddit. "
            "Não requer autenticação. Retorna títulos, scores, links e trechos dos posts. "
            "Ótimo para pesquisar opiniões, dicas e discussões sobre qualquer tema."
        ),
        parameters={
            "type": "object",
            "properties": {
                "subreddit": {
                    "type": "string",
                    "description": "Nome do subreddit sem r/. Ex: 'LocalLLaMA', 'programming', 'brasil'"
                },
                "query": {
                    "type": "string",
                    "description": "Termo de pesquisa"
                },
                "limit": {
                    "type": "integer",
                    "description": "Número máximo de resultados (padrão: 15, máximo: 100)",
                    "default": 15
                },
                "sort": {
                    "type": "string",
                    "description": "Ordenação: relevance, hot, top, new, comments",
                    "default": "relevance",
                    "enum": ["relevance", "hot", "top", "new", "comments"]
                }
            },
            "required": ["subreddit", "query"]
        },
    )

    logger.info("Plugin Agent-Reach: 3 ferramentas sociais registradas (social_read, youtube_transcript, reddit_search).")
