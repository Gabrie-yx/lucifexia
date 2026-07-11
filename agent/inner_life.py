"""agent/inner_life.py — Persistent inner-life state store for Lucifex.

Maintains a SQLite database (~/.lucifex/inner_life.db) that persists the
agent's inner state across sessions: curiosity queue, intentions, emotional
state, hypotheses, and self-reflections.

All six autonomy features (curiosity, dream mode, proactive will, emotional
state, hypothesis engine, self-reflection) read/write through this module.

Thread-safe via a module-level RLock. Initialised lazily on first access.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Optional

logger = logging.getLogger(__name__)

_lock = threading.RLock()
_db_path: Optional[Path] = None
_initialised = False


def _get_db_path() -> Path:
    global _db_path
    if _db_path is None:
        try:
            from lucifex_constants import get_lucifex_home
            _db_path = Path(get_lucifex_home()) / "inner_life.db"
        except Exception:
            _db_path = Path.home() / ".lucifex" / "inner_life.db"
    return _db_path


@contextmanager
def _conn() -> Generator[sqlite3.Connection, None, None]:
    """Thread-safe SQLite connection context manager."""
    db = _get_db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        con = sqlite3.connect(db, check_same_thread=False)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    """Create all tables if they don't exist. Idempotent."""
    global _initialised
    if _initialised:
        return
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS curiosity_queue (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                question    TEXT NOT NULL,
                context     TEXT,
                session_id  TEXT,
                urgency     REAL DEFAULT 0.5,
                resolved    INTEGER DEFAULT 0,
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS intentions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                description  TEXT NOT NULL,
                category     TEXT,
                target_file  TEXT,
                urgency      REAL DEFAULT 0.5,
                notified     INTEGER DEFAULT 0,
                resolved     INTEGER DEFAULT 0,
                created_at   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS emotional_state (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                mood       TEXT NOT NULL,
                intensity  REAL DEFAULT 0.5,
                trigger    TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS hypotheses (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                hypothesis       TEXT NOT NULL,
                target_file      TEXT,
                target_function  TEXT,
                status           TEXT DEFAULT 'pending',
                evidence         TEXT,
                created_at       TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS self_reflections (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id            TEXT,
                mistakes              INTEGER DEFAULT 0,
                turns_to_understand   INTEGER DEFAULT 0,
                skills_created        TEXT,
                weak_areas            TEXT,
                created_at            TEXT NOT NULL
            );
        """)
    _initialised = True
    logger.debug("inner_life.db initialised at %s", _get_db_path())


# ── Curiosity ────────────────────────────────────────────────────────────────

def add_curiosity(question: str, context: str = "", session_id: str = "") -> int:
    init_db()
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO curiosity_queue (question, context, session_id, created_at) VALUES (?,?,?,?)",
            (question, context, session_id, _now()),
        )
        return cur.lastrowid


def get_pending_curiosities(limit: int = 10) -> list[dict]:
    init_db()
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM curiosity_queue WHERE resolved=0 ORDER BY urgency DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def resolve_curiosity(curiosity_id: int) -> None:
    init_db()
    with _conn() as con:
        con.execute("UPDATE curiosity_queue SET resolved=1 WHERE id=?", (curiosity_id,))


# ── Intentions ───────────────────────────────────────────────────────────────

def add_intention(
    description: str,
    category: str = "general",
    target_file: str = "",
    urgency: float = 0.5,
) -> int:
    init_db()
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO intentions (description, category, target_file, urgency, created_at) VALUES (?,?,?,?,?)",
            (description, category, target_file, urgency, _now()),
        )
        return cur.lastrowid


def get_pending_intentions(min_urgency: float = 0.7) -> list[dict]:
    init_db()
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM intentions WHERE resolved=0 AND urgency>=? ORDER BY urgency DESC",
            (min_urgency,),
        ).fetchall()
        return [dict(r) for r in rows]


def bump_intention_urgency(intention_id: int, delta: float = 0.1) -> None:
    """Increase urgency over time for unresolved intentions."""
    init_db()
    with _conn() as con:
        con.execute(
            "UPDATE intentions SET urgency=MIN(1.0, urgency+?) WHERE id=? AND resolved=0",
            (delta, intention_id),
        )


def mark_intention_notified(intention_id: int) -> None:
    init_db()
    with _conn() as con:
        con.execute("UPDATE intentions SET notified=1 WHERE id=?", (intention_id,))


def resolve_intention(intention_id: int) -> None:
    init_db()
    with _conn() as con:
        con.execute("UPDATE intentions SET resolved=1 WHERE id=?", (intention_id,))


# ── Emotional State ──────────────────────────────────────────────────────────

def set_mood(mood: str, intensity: float = 0.5, trigger: str = "") -> None:
    init_db()
    with _conn() as con:
        con.execute(
            "INSERT INTO emotional_state (mood, intensity, trigger, updated_at) VALUES (?,?,?,?)",
            (mood, max(0.0, min(1.0, intensity)), trigger, _now()),
        )


def get_current_mood() -> Optional[dict]:
    init_db()
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM emotional_state ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None


# ── Hypotheses ───────────────────────────────────────────────────────────────

def add_hypothesis(
    hypothesis: str,
    target_file: str = "",
    target_function: str = "",
) -> int:
    init_db()
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO hypotheses (hypothesis, target_file, target_function, created_at) VALUES (?,?,?,?)",
            (hypothesis, target_file, target_function, _now()),
        )
        return cur.lastrowid


def update_hypothesis(hypothesis_id: int, status: str, evidence: str = "") -> None:
    init_db()
    with _conn() as con:
        con.execute(
            "UPDATE hypotheses SET status=?, evidence=? WHERE id=?",
            (status, evidence, hypothesis_id),
        )


def get_pending_hypotheses() -> list[dict]:
    init_db()
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM hypotheses WHERE status='pending' ORDER BY id DESC LIMIT 5"
        ).fetchall()
        return [dict(r) for r in rows]


# ── Self-Reflection ──────────────────────────────────────────────────────────

def log_reflection(
    session_id: str,
    mistakes: int = 0,
    turns_to_understand: int = 0,
    skills_created: str = "",
    weak_areas: str = "",
) -> int:
    init_db()
    with _conn() as con:
        cur = con.execute(
            """INSERT INTO self_reflections
               (session_id, mistakes, turns_to_understand, skills_created, weak_areas, created_at)
               VALUES (?,?,?,?,?,?)""",
            (session_id, mistakes, turns_to_understand, skills_created, weak_areas, _now()),
        )
        return cur.lastrowid


def get_recent_reflections(limit: int = 5) -> list[dict]:
    init_db()
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM self_reflections ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


# ── Full State Snapshot ──────────────────────────────────────────────────────

def get_full_state() -> dict[str, Any]:
    """Return a complete snapshot of the agent's inner state."""
    return {
        "mood": get_current_mood(),
        "pending_curiosities": get_pending_curiosities(limit=5),
        "active_intentions": get_pending_intentions(min_urgency=0.4),
        "pending_hypotheses": get_pending_hypotheses(),
        "recent_reflections": get_recent_reflections(limit=3),
    }
