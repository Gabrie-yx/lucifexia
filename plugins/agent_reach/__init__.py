"""Agent-Reach plugin — leitura de redes sociais sem custo de API.

Expõe três ferramentas:

- ``social_read(platform, query_or_url, limit?)``
  Lê ou pesquisa conteúdo em Twitter/X, Reddit, GitHub, XiaoHongShu, Bilibili.
  Implementação nativa robusta; não depende do pacote agent-reach.

- ``youtube_transcript(url, language?)``
  Baixa transcrição completa de vídeo YouTube via youtube-transcript-api.
  Compatível com versões 0.5.x a 1.x (dicts e FetchedTranscriptSnippet).

- ``reddit_search(subreddit, query, limit?, sort?)``
  Pesquisa posts em subreddit via API JSON pública do Reddit.
  Headers de browser real para evitar 403.

Instalação automática: instala youtube-transcript-api via pip na primeira
chamada de youtube_transcript.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import urllib.parse
import urllib.request
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


def _ensure_yt_transcript() -> bool:
    """Garante que youtube-transcript-api está instalado."""
    try:
        import youtube_transcript_api  # noqa: F401
        return True
    except ImportError:
        pass
    logger.info("youtube-transcript-api não encontrado — instalando...")
    if _pip_install("youtube-transcript-api"):
        try:
            import youtube_transcript_api  # noqa: F401
            return True
        except ImportError:
            pass
    return False


# ---------------------------------------------------------------------------
# Headers robustos para requests HTTP — evita 403 em Reddit/outros
# ---------------------------------------------------------------------------

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "DNT": "1",
    "Connection": "keep-alive",
}


def _http_get_json(url: str, extra_headers: dict | None = None, timeout: int = 15) -> Any:
    """Faz GET com headers de browser, retorna JSON parseado."""
    headers = {**_BROWSER_HEADERS, **(extra_headers or {})}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        # urllib não descomprime gzip automaticamente em todos os casos
        if resp.headers.get("Content-Encoding") == "gzip":
            import gzip
            raw = gzip.decompress(raw)
        return json.loads(raw)


# ---------------------------------------------------------------------------
# Implementação das ferramentas
# ---------------------------------------------------------------------------

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
    limit = max(1, min(int(limit), 50))

    # Roteamento por plataforma
    if platform in ("reddit",):
        return _read_reddit(query_or_url, limit)
    elif platform in ("github",):
        return _read_github(query_or_url, limit)
    elif platform in ("twitter", "x"):
        return _read_twitter_fallback(query_or_url, limit)
    elif platform in ("xiaohongshu", "xhs"):
        return (
            "XiaoHongShu requer autenticação por cookie — use web_extract_stealth "
            "com a URL do post para extrair conteúdo diretamente."
        )
    elif platform in ("bilibili",):
        return _read_bilibili(query_or_url, limit)
    else:
        return (
            f"Plataforma '{platform}' não reconhecida.\n"
            "Plataformas suportadas: twitter, reddit, github, xiaohongshu, bilibili."
        )


def _read_reddit(query_or_url: str, limit: int) -> str:
    """Lê Reddit via API JSON pública."""
    try:
        if query_or_url.startswith("http"):
            # URL direta de post ou subreddit
            url = query_or_url.rstrip("/") + ".json?limit=" + str(limit)
        else:
            url = (
                f"https://www.reddit.com/search.json"
                f"?q={urllib.parse.quote(query_or_url)}&limit={limit}&sort=relevance"
            )

        data = _http_get_json(url)
        posts = data.get("data", {}).get("children", [])
        if not posts:
            return "Nenhum resultado encontrado no Reddit."

        lines = []
        for p in posts[:limit]:
            d = p.get("data", {})
            title = d.get("title", "?")
            score = d.get("score", 0)
            permalink = d.get("permalink", "")
            sub = d.get("subreddit", "?")
            comments = d.get("num_comments", 0)
            snippet = (d.get("selftext") or "")[:200]
            lines.append(
                f"📌 **{title}**\n"
                f"   r/{sub} | ↑{score} | 💬{comments}\n"
                f"   https://reddit.com{permalink}"
                + (f"\n   {snippet}..." if snippet else "")
            )
        return "\n\n".join(lines)

    except Exception as exc:
        return f"[ERRO] Falha ao ler Reddit: {exc}"


def _read_github(query_or_url: str, limit: int) -> str:
    """Pesquisa repositórios no GitHub via API pública."""
    try:
        if "github.com/" in query_or_url:
            # URL direta de repo — extrai owner/repo e chama API
            parts = query_or_url.rstrip("/").split("github.com/")[-1].split("/")
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]
                url = f"https://api.github.com/repos/{owner}/{repo}"
                data = _http_get_json(url, extra_headers={"Accept": "application/vnd.github+json"})
                return (
                    f"📦 **{data.get('full_name', '?')}**\n"
                    f"   ⭐ {data.get('stargazers_count', 0)} | "
                    f"🍴 {data.get('forks_count', 0)} | "
                    f"👁️ {data.get('watchers_count', 0)}\n"
                    f"   {data.get('description', '')}\n"
                    f"   Linguagem: {data.get('language', '?')}\n"
                    f"   {data.get('html_url', '')}"
                )
        url = (
            f"https://api.github.com/search/repositories"
            f"?q={urllib.parse.quote(query_or_url)}&per_page={limit}&sort=stars"
        )
        data = _http_get_json(
            url,
            extra_headers={"Accept": "application/vnd.github+json"},
        )
        items = data.get("items", [])
        if not items:
            return "Nenhum repositório encontrado no GitHub."
        lines = [
            f"⭐ **{r['full_name']}** ({r.get('stargazers_count', 0)} ⭐)\n"
            f"   {r.get('description', '')}\n"
            f"   {r.get('language', '?')} | {r.get('html_url', '')}"
            for r in items[:limit]
        ]
        return f"Repositórios GitHub para '{query_or_url}':\n\n" + "\n\n".join(lines)

    except Exception as exc:
        return f"[ERRO] Falha ao ler GitHub: {exc}"


def _read_twitter_fallback(query_or_url: str, limit: int) -> str:
    """Twitter/X não tem API pública gratuita. Orienta sobre alternativas."""
    if query_or_url.startswith("http") and "twitter.com" in query_or_url or "x.com" in query_or_url:
        return (
            "Twitter/X não permite scraping sem autenticação desde 2023.\n\n"
            "Alternativas:\n"
            "• Use web_extract_stealth para tentar extrair o conteúdo da URL diretamente\n"
            "  (pode ser bloqueado por login wall)\n"
            "• Use Nitter como proxy: https://nitter.net/[usuario]\n"
            f"  → Tente: web_extract_stealth(url='https://nitter.net/{query_or_url.split('/')[-1]}')"
        )
    # Tenta busca via Nitter (instância pública de Twitter)
    try:
        nitter_url = f"https://nitter.net/search?q={urllib.parse.quote(query_or_url)}&f=tweets"
        return (
            f"Twitter/X não tem API pública gratuita.\n\n"
            f"Para buscar tweets sobre '{query_or_url}', use:\n"
            f"  web_extract_stealth(url='{nitter_url}')\n\n"
            f"Ou instale twscrape para coleta autenticada:\n"
            f"  pip install twscrape"
        )
    except Exception:
        return "Twitter/X: sem API pública gratuita disponível."


def _read_bilibili(query_or_url: str, limit: int) -> str:
    """Pesquisa vídeos no Bilibili via API pública."""
    try:
        if "bilibili.com/video/" in query_or_url:
            # URL de vídeo direto
            bvid = query_or_url.split("/video/")[-1].split("?")[0].rstrip("/")
            url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
            data = _http_get_json(url)
            d = data.get("data", {})
            stat = d.get("stat", {})
            return (
                f"🎬 **{d.get('title', '?')}**\n"
                f"   UP: {d.get('owner', {}).get('name', '?')}\n"
                f"   👁️ {stat.get('view', 0)} | 👍 {stat.get('like', 0)} | "
                f"💬 {stat.get('reply', 0)}\n"
                f"   {d.get('desc', '')}\n"
                f"   https://bilibili.com/video/{bvid}"
            )
        url = (
            f"https://api.bilibili.com/x/web-interface/search/all/v2"
            f"?keyword={urllib.parse.quote(query_or_url)}&page=1&page_size={limit}"
        )
        data = _http_get_json(url)
        videos = data.get("data", {}).get("result", [])
        if isinstance(videos, list):
            video_list = next(
                (r.get("data", []) for r in videos if r.get("result_type") == "video"),
                []
            )
        else:
            video_list = []
        if not video_list:
            return f"Nenhum vídeo encontrado no Bilibili para: {query_or_url}"
        lines = []
        for v in video_list[:limit]:
            title = v.get('title', '?').replace('<em class="keyword">', '').replace('</em>', '')
            lines.append(
                f"🎬 {title}\n"
                f"   UP: {v.get('author', '?')} | 👁️ {v.get('play', 0)}\n"
                f"   https://bilibili.com/video/{v.get('bvid', '')}"
            )
        return f"Bilibili — '{query_or_url}':\n\n" + "\n\n".join(lines)
    except Exception as exc:
        return f"[ERRO] Falha ao ler Bilibili: {exc}"


def youtube_transcript(
    url: str,
    language: str = "pt",
) -> str:
    """Baixa a transcrição completa de um vídeo do YouTube.

    Compatível com youtube-transcript-api 0.5.x a 1.x.
    Suporta tanto segmentos dict (antigos) quanto objetos FetchedTranscriptSnippet (novos).

    Args:
        url: URL do vídeo YouTube (youtube.com/watch?v=... ou youtu.be/...).
        language: Código de idioma preferido (padrão: 'pt').
                  Faz fallback automático para 'en' se não disponível.

    Returns:
        Transcrição completa do vídeo como texto contínuo.
    """
    if not _ensure_yt_transcript():
        return (
            "❌ youtube-transcript-api não pôde ser instalado.\n"
            "Execute: pip install youtube-transcript-api"
        )

    try:
        import re
        from youtube_transcript_api import YouTubeTranscriptApi

        # Extrai video_id da URL
        vid_match = re.search(r"(?:v=|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})", url)
        if not vid_match:
            return f"[ERRO] Não foi possível extrair o ID do vídeo de: {url}"

        video_id = vid_match.group(1)

        # Tenta obter a lista de transcrições
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        except Exception as exc:
            # API mais antiga (< 0.6): tenta obter direto
            try:
                segments = YouTubeTranscriptApi.get_transcript(
                    video_id, languages=[language, "en", "pt-BR"]
                )
                text = _segments_to_text(segments)
                return f"[Transcrição YouTube | {len(segments)} segmentos]\n\n{text}"
            except Exception:
                return f"[ERRO] Falha ao obter transcrição de {url}: {exc}"

        # Tenta idiomas em ordem de preferência
        transcript = None
        lang_found = "?"
        for lang in [language, "en", "pt-BR", "pt-PT"]:
            try:
                # API nova: find_transcript([lang])
                try:
                    transcript = transcript_list.find_transcript([lang])
                    lang_found = lang
                    break
                except AttributeError:
                    # API intermediária
                    transcript = transcript_list.find_manually_created_transcript([lang])
                    lang_found = lang
                    break
            except Exception:
                continue

        if transcript is None:
            # Usa o primeiro disponível (manual ou gerado)
            available = list(transcript_list)
            if not available:
                return "[ERRO] Nenhuma transcrição disponível para este vídeo."
            transcript = available[0]
            lang_found = getattr(transcript, "language_code", "?")

        # Busca os segmentos — compatível com versões antigas e novas
        try:
            segments = transcript.fetch()
        except TypeError:
            # Versões antigas não aceitam args
            segments = transcript.fetch()  # type: ignore

        text = _segments_to_text(segments)
        seg_count = len(list(segments)) if hasattr(segments, "__len__") else "?"
        return (
            f"[Transcrição YouTube | idioma: {lang_found} | {seg_count} segmentos]\n\n{text}"
        )

    except Exception as exc:
        logger.error("youtube_transcript falhou para %s: %s", url, exc)
        return f"[ERRO] Falha ao obter transcrição de {url}: {exc}"


def _segments_to_text(segments) -> str:
    """Converte segmentos de transcrição para texto.

    Compatível com:
    - API antiga (< 0.6): lista de dicts {'text': ..., 'start': ..., 'duration': ...}
    - API nova (≥ 0.6): lista de FetchedTranscriptSnippet com atributo .text
    """
    parts = []
    for seg in segments:
        if isinstance(seg, dict):
            parts.append(seg.get("text", ""))
        else:
            # FetchedTranscriptSnippet ou similar — acessa .text
            parts.append(getattr(seg, "text", str(seg)))
    return " ".join(p.strip() for p in parts if p.strip())


def reddit_search(
    subreddit: str,
    query: str,
    limit: int = 15,
    sort: str = "relevance",
) -> str:
    """Pesquisa posts em um subreddit usando a API JSON pública do Reddit.

    Não requer autenticação. Usa headers de browser real para evitar 403.

    Args:
        subreddit: Nome do subreddit sem r/. Ex: "LocalLLaMA", "programming"
        query: Termo de pesquisa.
        limit: Número máximo de resultados (padrão: 15, máximo: 100).
        sort: Ordenação: relevance, hot, top, new, comments.

    Returns:
        Lista de posts com título, score, URL e trecho do texto.
    """
    try:
        limit = min(max(int(limit), 1), 100)
        sort = sort if sort in ("relevance", "hot", "top", "new", "comments") else "relevance"

        url = (
            f"https://www.reddit.com/r/{urllib.parse.quote(subreddit)}/search.json"
            f"?q={urllib.parse.quote(query)}&restrict_sr=1&sort={sort}&limit={limit}"
        )

        data = _http_get_json(url)
        posts = data.get("data", {}).get("children", [])

        if not posts:
            return f"Nenhum post encontrado em r/{subreddit} para: {query}"

        lines = []
        for p in posts:
            d = p.get("data", {})
            title = d.get("title", "?")
            score = d.get("score", 0)
            permalink = d.get("permalink", "")
            selftext = (d.get("selftext") or "")[:300]
            num_comments = d.get("num_comments", 0)
            flair = d.get("link_flair_text") or ""

            lines.append(
                f"📌 **{title}**"
                + (f" [{flair}]" if flair else "") + "\n"
                f"   ↑{score} pontos | 💬{num_comments} comentários\n"
                f"   https://reddit.com{permalink}"
                + (f"\n   {selftext}..." if selftext else "")
            )

        return f"Resultados em r/{subreddit} para '{query}' ({sort}):\n\n" + "\n\n".join(lines)

    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            return (
                f"[403 Bloqueado] Reddit recusou a requisição para r/{subreddit}.\n"
                "Tente acessar via browser ou use a URL direta com web_extract_stealth:\n"
                f"  web_extract_stealth(url='https://www.reddit.com/r/{subreddit}/search/?q={urllib.parse.quote(query)}')"
            )
        return f"[ERRO HTTP {exc.code}] Falha ao pesquisar r/{subreddit}: {exc}"
    except Exception as exc:
        logger.error("reddit_search falhou: %s", exc)
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
            "Suporta Reddit, GitHub, Bilibili com dados reais. "
            "Twitter/X: orienta sobre alternativas (login obrigatório desde 2023). "
            "query_or_url pode ser URL direta ou termo de pesquisa."
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
            "Instala youtube-transcript-api automaticamente se necessário. "
            "Suporta múltiplos idiomas com fallback para inglês."
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
                    "description": "Código de idioma preferido: 'pt', 'en', 'es' (padrão: 'pt')",
                    "default": "pt"
                }
            },
            "required": ["url"]
        },
    )

    registry.register(
        name="reddit_search",
        func=reddit_search,
        description=(
            "Pesquisa posts em um subreddit via API JSON pública do Reddit. "
            "Não requer autenticação. Retorna títulos, scores, links e trechos. "
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

    logger.info(
        "Plugin Agent-Reach: 3 ferramentas registradas "
        "(social_read, youtube_transcript, reddit_search)."
    )
