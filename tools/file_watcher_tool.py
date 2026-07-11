"""tools/file_watcher_tool.py — File Intelligence for Lucifex.

Monitors filesystem folders and acts intelligently on new files:
- Auto-rename PDFs to their real title (extracted from content)
- Auto-organize files by type into structured folders
- Watch for new files and notify the agent
- Semantic search over recent file activity

Uses watchdog for real-time file system monitoring.
Registered tools: file_watch, file_organize, file_recent, file_rename_smart
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from tools.registry import registry

logger = logging.getLogger(__name__)

_watch_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_db_path: Optional[Path] = None

# ── Type → Folder mapping ─────────────────────────────────────────────────────
_EXTENSION_MAP = {
    # Documents
    ".pdf": "Documents/PDFs",
    ".docx": "Documents/Word",
    ".doc": "Documents/Word",
    ".xlsx": "Documents/Spreadsheets",
    ".xls": "Documents/Spreadsheets",
    ".pptx": "Documents/Presentations",
    ".txt": "Documents/Text",
    # Code
    ".py": "Code/Python",
    ".js": "Code/JavaScript",
    ".ts": "Code/TypeScript",
    ".go": "Code/Go",
    ".rs": "Code/Rust",
    # Images
    ".png": "Images",
    ".jpg": "Images",
    ".jpeg": "Images",
    ".gif": "Images",
    ".svg": "Images",
    ".webp": "Images",
    # Archives
    ".zip": "Archives",
    ".tar": "Archives",
    ".gz": "Archives",
    ".7z": "Archives",
    # Data
    ".json": "Data",
    ".csv": "Data",
    ".xml": "Data",
    ".yaml": "Data",
    ".yml": "Data",
}

# Invoice/receipt patterns for auto-filing
_INVOICE_PATTERN = re.compile(
    r"invoice|receipt|fatura|nota fiscal|recibo|payment|pagamento",
    re.IGNORECASE,
)


def _get_db() -> Path:
    global _db_path
    if _db_path is None:
        try:
            from lucifex_constants import get_lucifex_home
            _db_path = Path(get_lucifex_home()) / "file_activity.db"
        except Exception:
            _db_path = Path.home() / ".lucifex" / "file_activity.db"
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    return _db_path


def _init_db() -> None:
    with sqlite3.connect(_get_db()) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS file_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type  TEXT,
                file_path   TEXT,
                file_name   TEXT,
                extension   TEXT,
                size_bytes  INTEGER,
                action_taken TEXT,
                occurred_at TEXT NOT NULL
            )
        """)


def _log_event(event_type: str, path: Path, action: str = "") -> None:
    try:
        _init_db()
        with sqlite3.connect(_get_db()) as con:
            con.execute("""
                INSERT INTO file_events (event_type, file_path, file_name, extension, size_bytes, action_taken, occurred_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event_type,
                str(path),
                path.name,
                path.suffix.lower(),
                path.stat().st_size if path.exists() else 0,
                action,
                datetime.now(timezone.utc).isoformat(),
            ))
    except Exception as exc:
        logger.debug("Failed to log file event: %s", exc)


# ── PDF Title Extraction ──────────────────────────────────────────────────────

def _extract_pdf_title(pdf_path: Path) -> Optional[str]:
    """Extract the real title from a PDF file."""
    try:
        import pypdf
        with open(pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            meta = reader.metadata
            if meta and meta.title:
                return meta.title.strip()[:80]
            # First page text fallback
            if reader.pages:
                text = reader.pages[0].extract_text() or ""
                first_line = text.strip().splitlines()[0] if text.strip() else ""
                if len(first_line) > 5:
                    return first_line[:80]
    except ImportError:
        pass
    except Exception as exc:
        logger.debug("PDF title extraction failed: %s", exc)
    return None


def _smart_rename_pdf(pdf_path: Path) -> Optional[Path]:
    """Rename a PDF to its real title if different from current name."""
    title = _extract_pdf_title(pdf_path)
    if not title:
        return None

    # Sanitize filename
    safe = re.sub(r'[<>:"/\\|?*]', "", title)
    safe = re.sub(r"\s+", "_", safe.strip())
    if not safe:
        return None

    new_path = pdf_path.parent / f"{safe}.pdf"
    if new_path == pdf_path or new_path.exists():
        return None

    try:
        pdf_path.rename(new_path)
        logger.info("PDF renamed: %s → %s", pdf_path.name, new_path.name)
        return new_path
    except Exception as exc:
        logger.debug("PDF rename failed: %s", exc)
        return None


# ── Auto-Organize ─────────────────────────────────────────────────────────────

def _auto_organize_file(file_path: Path, target_root: Path) -> Optional[str]:
    """Move a file to the appropriate subfolder based on extension."""
    ext = file_path.suffix.lower()
    subfolder = _EXTENSION_MAP.get(ext)
    if not subfolder:
        return None

    # Special case: invoice/receipt detection for PDFs
    if ext == ".pdf" and _INVOICE_PATTERN.search(file_path.name):
        year = datetime.now().strftime("%Y")
        subfolder = f"Documents/Finance/{year}"

    target_dir = target_root / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / file_path.name

    # Avoid overwriting
    if target.exists():
        stem = file_path.stem
        ts = datetime.now().strftime("%H%M%S")
        target = target_dir / f"{stem}_{ts}{ext}"

    try:
        shutil.move(str(file_path), str(target))
        logger.info("File organized: %s → %s", file_path.name, target)
        return str(target)
    except Exception as exc:
        logger.debug("File organize failed: %s", exc)
        return None


# ── Watchdog Integration ──────────────────────────────────────────────────────

_watched_paths: dict[str, dict] = {}  # path → {auto_organize: bool, auto_rename: bool}


def _start_watchdog(watch_path: Path, auto_organize: bool, auto_rename: bool) -> None:
    """Start a watchdog observer for a path."""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        class _Handler(FileSystemEventHandler):
            def on_created(self, event):
                if event.is_directory:
                    return
                fp = Path(event.src_path)
                logger.debug("File created: %s", fp.name)
                _log_event("created", fp)

                if auto_rename and fp.suffix.lower() == ".pdf":
                    new_path = _smart_rename_pdf(fp)
                    if new_path:
                        _log_event("renamed", new_path, f"auto-renamed from {fp.name}")
                        fp = new_path

                if auto_organize:
                    result = _auto_organize_file(fp, watch_path.parent)
                    if result:
                        _log_event("organized", Path(result), f"moved from {watch_path}")

        observer = Observer()
        observer.schedule(_Handler(), str(watch_path), recursive=False)
        observer.daemon = True
        observer.start()
        logger.info("Watchdog started on: %s", watch_path)
        return observer
    except ImportError:
        logger.debug("watchdog not installed — file monitoring unavailable. pip install watchdog")
        return None


# ── Tool Implementations ──────────────────────────────────────────────────────

def file_watch(
    path: str,
    auto_organize: bool = False,
    auto_rename: bool = True,
) -> str:
    """Start watching a folder for new files.

    path: absolute path to folder to watch.
    auto_organize: automatically move files to type-appropriate subfolders.
    auto_rename: automatically rename PDFs to their real title.
    """
    watch_path = Path(path)
    if not watch_path.exists():
        return json.dumps({"error": f"Path does not exist: {path}"})

    _watched_paths[str(watch_path)] = {
        "auto_organize": auto_organize,
        "auto_rename": auto_rename,
    }
    _start_watchdog(watch_path, auto_organize, auto_rename)
    return json.dumps({
        "watching": str(watch_path),
        "auto_organize": auto_organize,
        "auto_rename": auto_rename,
    })


def file_organize(source_folder: str, target_folder: Optional[str] = None) -> str:
    """Organize all files in a folder by type into subfolders.

    source_folder: folder containing unorganized files.
    target_folder: where to create subfolders (defaults to same as source).
    """
    source = Path(source_folder)
    target = Path(target_folder) if target_folder else source
    if not source.exists():
        return json.dumps({"error": f"Folder not found: {source_folder}"})

    organized = []
    skipped = []
    for f in source.iterdir():
        if f.is_file():
            result = _auto_organize_file(f, target)
            if result:
                organized.append({"file": f.name, "moved_to": result})
            else:
                skipped.append(f.name)

    return json.dumps({
        "organized": len(organized),
        "skipped": len(skipped),
        "details": organized[:10],
    })


def file_recent(hours: int = 24, folder: Optional[str] = None) -> str:
    """List recently created or modified files tracked by the file watcher."""
    _init_db()
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    query = "SELECT * FROM file_events WHERE occurred_at > ? ORDER BY occurred_at DESC LIMIT 20"
    params = [cutoff]

    if folder:
        query = "SELECT * FROM file_events WHERE occurred_at > ? AND file_path LIKE ? ORDER BY occurred_at DESC LIMIT 20"
        params.append(f"%{folder}%")

    with sqlite3.connect(_get_db()) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(query, params).fetchall()

    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


def file_rename_smart(file_path: str) -> str:
    """Rename a PDF to its real document title extracted from content."""
    fp = Path(file_path)
    if not fp.exists():
        return json.dumps({"error": f"File not found: {file_path}"})

    if fp.suffix.lower() != ".pdf":
        return json.dumps({"error": "Smart rename currently supports PDF files only."})

    new_path = _smart_rename_pdf(fp)
    if new_path:
        return json.dumps({"success": True, "original": fp.name, "renamed_to": new_path.name})
    return json.dumps({"success": False, "message": "Could not extract title from PDF, or name is already correct."})


# ── Registration ──────────────────────────────────────────────────────────────

_tools = [
    ("file_watch", file_watch,
     "Start watching a folder for new files. Can auto-rename PDFs to their real title and auto-organize files by type.",
     {"path": {"type": "string"}, "auto_organize": {"type": "boolean", "default": False}, "auto_rename": {"type": "boolean", "default": True}},
     ["path"]),
    ("file_organize", file_organize,
     "Organize all files in a folder by automatically moving them into type-appropriate subfolders.",
     {"source_folder": {"type": "string"}, "target_folder": {"type": "string"}},
     ["source_folder"]),
    ("file_recent", file_recent,
     "List recently created or modified files tracked by the file watcher.",
     {"hours": {"type": "integer", "default": 24}, "folder": {"type": "string"}},
     []),
    ("file_rename_smart", file_rename_smart,
     "Rename a PDF file to its actual document title, extracted from the PDF content.",
     {"file_path": {"type": "string", "description": "Absolute path to the PDF file"}},
     ["file_path"]),
]

for _name, _fn, _desc, _props, _required in _tools:
    registry.register(
        name=_name,
        toolset="computer",
        schema={
            "name": _name,
            "description": _desc,
            "parameters": {"type": "object", "properties": _props, "required": _required},
        },
        handler=_fn,
        description=_desc,
        emoji="🗂️",
    )
