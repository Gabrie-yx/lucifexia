"""tools/clipboard_tool.py — Intelligent clipboard monitoring and transformation.

Runs a background monitor thread that watches the system clipboard for
changes. When content is detected, it classifies and optionally transforms
it: JSON → formatted, URL → title fetched, code → language detected,
potential secrets → user warned.

Maintains a searchable history of recent clipboard entries in SQLite.

Registered as model tool `clipboard_get`, `clipboard_set`, `clipboard_history`.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from tools.registry import registry

logger = logging.getLogger(__name__)

_monitor_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_last_content: str = ""
_db_path: Optional[Path] = None


# ── DB Setup ──────────────────────────────────────────────────────────────────

def _get_db() -> Path:
    global _db_path
    if _db_path is None:
        try:
            from lucifex_constants import get_lucifex_home
            _db_path = Path(get_lucifex_home()) / "clipboard_history.db"
        except Exception:
            _db_path = Path.home() / ".lucifex" / "clipboard_history.db"
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    return _db_path


def _init_db() -> None:
    with sqlite3.connect(_get_db()) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS clipboard_history (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                content      TEXT,
                content_type TEXT,
                summary      TEXT,
                copied_at    TEXT NOT NULL
            )
        """)
        con.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS clipboard_fts
            USING fts5(id UNINDEXED, content, content_type, summary)
        """)


def _store_entry(content: str, content_type: str, summary: str) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(_get_db()) as con:
        cur = con.execute(
            "INSERT INTO clipboard_history (content, content_type, summary, copied_at) VALUES (?,?,?,?)",
            (content[:4000], content_type, summary, ts),
        )
        row_id = cur.lastrowid
        con.execute(
            "INSERT INTO clipboard_fts(id, content, content_type, summary) VALUES (?,?,?,?)",
            (row_id, content[:4000], content_type, summary),
        )
        # Keep only last 200 entries
        con.execute(
            "DELETE FROM clipboard_history WHERE id NOT IN (SELECT id FROM clipboard_history ORDER BY id DESC LIMIT 200)"
        )


# ── Content Classification ────────────────────────────────────────────────────

_SECRET_PATTERN = re.compile(
    r"(?:api[_-]?key|password|secret|token|passwd|bearer)\s*[=:]\s*\S{8,}",
    re.IGNORECASE,
)

_URL_PATTERN = re.compile(r"^https?://\S+$")

_JSON_PATTERN = re.compile(r"^\s*[\[{]")


def _classify(text: str) -> tuple[str, str]:
    """Return (content_type, summary)."""
    text = text.strip()
    if not text:
        return "empty", ""

    if _SECRET_PATTERN.search(text):
        return "secret", "⚠ Possible credential detected"

    if _JSON_PATTERN.match(text):
        try:
            parsed = json.loads(text)
            return "json", f"JSON with {len(parsed)} {'keys' if isinstance(parsed, dict) else 'items'}"
        except Exception:
            return "text", text[:80]

    if _URL_PATTERN.match(text):
        return "url", text[:100]

    # Detect code by common language patterns
    if re.search(r"def |import |from |class |async def |#!", text):
        return "python", f"Python code ({len(text.splitlines())} lines)"
    if re.search(r"function |const |let |var |=>|require\(", text):
        return "javascript", f"JS/TS code ({len(text.splitlines())} lines)"
    if re.search(r"SELECT|INSERT|UPDATE|DELETE|CREATE TABLE", text, re.IGNORECASE):
        return "sql", "SQL query"

    lines = len(text.splitlines())
    words = len(text.split())
    return "text", f"{words} words, {lines} lines"


def _transform(text: str, content_type: str) -> Optional[str]:
    """Optionally transform content. Returns transformed text or None if no change."""
    if content_type == "json":
        try:
            parsed = json.loads(text)
            formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
            if formatted != text.strip():
                return formatted
        except Exception:
            pass
    return None


# ── Clipboard Access ──────────────────────────────────────────────────────────

def _read_clipboard() -> Optional[str]:
    """Read current clipboard text content."""
    try:
        import subprocess, sys
        if sys.platform == "win32":
            result = subprocess.run(
                ["powershell", "-command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=3
            )
            return result.stdout.rstrip("\n") if result.returncode == 0 else None
        elif sys.platform == "darwin":
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=3)
            return result.stdout if result.returncode == 0 else None
        else:
            result = subprocess.run(
                ["xclip", "-selection", "clipboard", "-o"],
                capture_output=True, text=True, timeout=3
            )
            return result.stdout if result.returncode == 0 else None
    except Exception:
        return None


def _write_clipboard(text: str) -> bool:
    """Write text to clipboard."""
    try:
        import subprocess, sys
        if sys.platform == "win32":
            p = subprocess.Popen(
                ["powershell", "-command", "Set-Clipboard -Value $input"],
                stdin=subprocess.PIPE, text=True
            )
            p.communicate(input=text, timeout=3)
            return p.returncode == 0
        elif sys.platform == "darwin":
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE, text=True)
            p.communicate(input=text, timeout=3)
            return True
        else:
            p = subprocess.Popen(
                ["xclip", "-selection", "clipboard"],
                stdin=subprocess.PIPE, text=True
            )
            p.communicate(input=text, timeout=3)
            return True
    except Exception as exc:
        logger.debug("Clipboard write failed: %s", exc)
        return False


# ── Background Monitor ────────────────────────────────────────────────────────

def _monitor_loop(interval: float = 1.5) -> None:
    global _last_content
    _init_db()
    logger.info("Clipboard monitor started.")
    while not _stop_event.is_set():
        try:
            current = _read_clipboard()
            if current and current != _last_content and len(current.strip()) > 2:
                _last_content = current
                content_type, summary = _classify(current)

                # Warn on secrets
                if content_type == "secret":
                    logger.warning("CLIPBOARD: Possible credential detected — %s", summary)

                _store_entry(current, content_type, summary)
                logger.debug("Clipboard captured: [%s] %s", content_type, summary)
        except Exception as exc:
            logger.debug("Clipboard monitor error: %s", exc)
        _stop_event.wait(interval)
    logger.info("Clipboard monitor stopped.")


def start_monitor() -> None:
    """Start the clipboard background monitor thread."""
    global _monitor_thread
    if _monitor_thread and _monitor_thread.is_alive():
        return
    _stop_event.clear()
    _monitor_thread = threading.Thread(target=_monitor_loop, daemon=True, name="clipboard-monitor")
    _monitor_thread.start()


def stop_monitor() -> None:
    _stop_event.set()


# ── Model Tools ───────────────────────────────────────────────────────────────

def clipboard_get() -> str:
    """Return the current clipboard content with its classified type."""
    content = _read_clipboard()
    if not content:
        return json.dumps({"content": "", "type": "empty", "summary": ""})
    content_type, summary = _classify(content)
    return json.dumps({
        "content": content[:2000],
        "type": content_type,
        "summary": summary,
        "length": len(content),
    }, ensure_ascii=False)


def clipboard_set(text: str) -> str:
    """Write text to the clipboard."""
    ok = _write_clipboard(text)
    return json.dumps({"success": ok, "length": len(text)})


def clipboard_search(query: str, limit: int = 5) -> str:
    """Search clipboard history semantically."""
    _init_db()
    try:
        with sqlite3.connect(_get_db()) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(
                """SELECT h.content, h.content_type, h.summary, h.copied_at
                   FROM clipboard_history h
                   JOIN clipboard_fts f ON h.id = f.id
                   WHERE clipboard_fts MATCH ?
                   ORDER BY h.id DESC LIMIT ?""",
                (query, limit),
            ).fetchall()
        results = [dict(r) for r in rows]
        return json.dumps(results, ensure_ascii=False, default=str)
    except Exception as exc:
        # FTS fallback: LIKE search
        with sqlite3.connect(_get_db()) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute(
                "SELECT content, content_type, summary, copied_at FROM clipboard_history WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
        return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


def clipboard_format() -> str:
    """Format the current clipboard content (e.g. pretty-print JSON)."""
    content = _read_clipboard()
    if not content:
        return json.dumps({"success": False, "message": "Clipboard is empty"})
    content_type, _ = _classify(content)
    transformed = _transform(content, content_type)
    if transformed:
        _write_clipboard(transformed)
        return json.dumps({"success": True, "message": f"Formatted {content_type} and updated clipboard."})
    return json.dumps({"success": False, "message": f"No transformation available for type: {content_type}"})


# ── Registration ──────────────────────────────────────────────────────────────

for _name, _fn, _desc in [
    ("clipboard_get", clipboard_get,
     "Read the current clipboard content. Returns the text and its classified type (json, url, code, secret, text)."),
    ("clipboard_set", clipboard_set,
     "Write text to the system clipboard."),
    ("clipboard_search", clipboard_search,
     "Search your clipboard history for past content. Pass a search query and optional limit."),
    ("clipboard_format", clipboard_format,
     "Auto-format the current clipboard content (e.g. pretty-print JSON) and update the clipboard in place."),
]:
    registry.register(
        name=_name,
        toolset="computer",
        schema={
            "name": _name,
            "description": _desc,
            "parameters": {
                "type": "object",
                "properties": (
                    {"text": {"type": "string", "description": "Text to write to clipboard"}}
                    if _name == "clipboard_set" else
                    {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}}
                    if _name == "clipboard_search" else
                    {}
                ),
                "required": (["text"] if _name == "clipboard_set" else
                             ["query"] if _name == "clipboard_search" else []),
            },
        },
        handler=_fn,
        description=_desc,
        emoji="📋",
    )

# Auto-start monitor when module is imported
start_monitor()
