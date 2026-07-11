"""agent/theory_of_mind.py — User knowledge modelling for Lucifex.

The agent maintains a persistent model of what the user knows, doesn't know,
and what they think they know but may be wrong about. This enables:

1. Calibrated explanations — technical depth matched to demonstrated knowledge
2. Blind-spot detection — proactive correction before errors are made
3. Learning curve tracking — the agent knows what concepts you've mastered

Stored in SQLite. Updated each session from the conversation.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_lock = threading.RLock()
_db_path: Optional[Path] = None

# Expertise levels for calibration
_EXPERTISE_LEVELS = {
    1: "beginner",
    2: "intermediate",
    3: "advanced",
    4: "expert",
}

# Patterns that reveal knowledge level
_EXPERT_SIGNALS = [
    r"O\(n\)|O\(log n\)|big.?O",
    r"idempotent|referential.?transparent|monad",
    r"CAP theorem|eventual.?consistency",
    r"memory.?barrier|race.?condition|mutex",
    r"tail.?recursion|memoiz",
]
_BEGINNER_SIGNALS = [
    r"how do I|what is a|what does .+ mean|can you explain",
    r"I'm new to|just started|learning",
    r"syntax error|why doesn't this work",
]
_MISCONCEPTION_PATTERNS = [
    (r"mutable.?default.?argument|def.+\(\w+=\[\]", "Python mutable default arguments are shared across all calls"),
    (r"float.+==|== .+\.\d+", "Floating point equality comparison is unreliable — use math.isclose()"),
    (r"except.+Exception.+pass|bare.+except", "Catching and silencing all exceptions hides bugs"),
    (r"SELECT \*", "SELECT * in production queries causes performance issues and schema coupling"),
    (r"global\s+\w+\s*=", "Global mutable state makes code unpredictable and hard to test"),
]


def _get_db() -> Path:
    global _db_path
    if _db_path is None:
        try:
            from lucifex_constants import get_lucifex_home
            _db_path = Path(get_lucifex_home()) / "theory_of_mind.db"
        except Exception:
            _db_path = Path.home() / ".lucifex" / "theory_of_mind.db"
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    return _db_path


@contextmanager
def _conn():
    with _lock:
        con = sqlite3.connect(_get_db(), check_same_thread=False)
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
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS user_concepts (
                concept         TEXT PRIMARY KEY,
                domain          TEXT DEFAULT 'general',
                expertise_level INTEGER DEFAULT 2,
                evidence        TEXT,
                updated_at      TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_misconceptions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern     TEXT NOT NULL,
                description TEXT NOT NULL,
                session_id  TEXT,
                corrected   INTEGER DEFAULT 0,
                detected_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS domain_expertise (
                domain          TEXT PRIMARY KEY,
                level           INTEGER DEFAULT 2,
                evidence_count  INTEGER DEFAULT 0,
                updated_at      TEXT NOT NULL
            );
        """)


# ── Knowledge Updating ────────────────────────────────────────────────────────

def update_from_message(text: str, session_id: str = "", from_user: bool = True) -> dict:
    """Analyse a message and update the user knowledge model.

    Returns dict of detected signals and any misconceptions found.
    """
    init_db()
    signals = {"expert": [], "beginner": [], "misconceptions": []}

    if from_user:
        # Check expertise signals
        for pattern in _EXPERT_SIGNALS:
            if re.search(pattern, text, re.IGNORECASE):
                signals["expert"].append(pattern)

        for pattern in _BEGINNER_SIGNALS:
            if re.search(pattern, text, re.IGNORECASE):
                signals["beginner"].append(pattern)

        # Check for misconceptions
        for pattern, description in _MISCONCEPTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                signals["misconceptions"].append(description)
                _record_misconception(pattern, description, session_id)

        # Update domain expertise
        _update_expertise_signals(text, signals)

    return signals


def _update_expertise_signals(text: str, signals: dict) -> None:
    """Adjust expertise levels based on detected signals."""
    expert_boost = len(signals["expert"]) * 0.5
    beginner_drag = len(signals["beginner"]) * 0.3

    domains_mentioned = _extract_domains(text)
    if not domains_mentioned:
        return

    with _conn() as con:
        for domain in domains_mentioned:
            row = con.execute("SELECT * FROM domain_expertise WHERE domain=?", (domain,)).fetchone()
            if row:
                current = row["level"]
                new_level = max(1, min(4, current + expert_boost - beginner_drag))
                con.execute("""
                    UPDATE domain_expertise SET level=?, evidence_count=evidence_count+1, updated_at=?
                    WHERE domain=?
                """, (round(new_level), _now(), domain))
            else:
                initial = 2 + expert_boost - beginner_drag
                con.execute("""
                    INSERT INTO domain_expertise (domain, level, evidence_count, updated_at)
                    VALUES (?, ?, 1, ?)
                """, (domain, max(1, min(4, round(initial))), _now()))


def _extract_domains(text: str) -> list[str]:
    """Detect technology/domain keywords in text."""
    domain_keywords = {
        "python": ["python", "django", "flask", "fastapi", "asyncio", "pandas"],
        "javascript": ["javascript", "typescript", "react", "node", "vue", "next.js"],
        "databases": ["sql", "postgres", "mysql", "mongodb", "redis", "sqlite", "query"],
        "systems": ["docker", "kubernetes", "linux", "bash", "nginx", "systemd"],
        "ml": ["pytorch", "tensorflow", "model", "training", "loss", "gradient", "neural"],
        "security": ["oauth", "jwt", "xss", "csrf", "encryption", "auth", "ssl"],
        "distributed": ["microservices", "kafka", "rabbitmq", "grpc", "rest", "api"],
    }
    text_lower = text.lower()
    return [domain for domain, keywords in domain_keywords.items()
            if any(kw in text_lower for kw in keywords)]


def _record_misconception(pattern: str, description: str, session_id: str) -> None:
    with _conn() as con:
        con.execute("""
            INSERT INTO user_misconceptions (pattern, description, session_id, detected_at)
            VALUES (?, ?, ?, ?)
        """, (pattern, description, session_id, _now()))


# ── Query API ─────────────────────────────────────────────────────────────────

def get_active_misconceptions() -> list[dict]:
    """Return uncorrected misconceptions for the user."""
    init_db()
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM user_misconceptions WHERE corrected=0 ORDER BY detected_at DESC LIMIT 5"
        ).fetchall()
        return [dict(r) for r in rows]


def mark_misconception_corrected(misconception_id: int) -> None:
    init_db()
    with _conn() as con:
        con.execute("UPDATE user_misconceptions SET corrected=1 WHERE id=?", (misconception_id,))


def get_domain_expertise() -> dict:
    """Return expertise levels across all detected domains."""
    init_db()
    with _conn() as con:
        rows = con.execute(
            "SELECT domain, level, evidence_count FROM domain_expertise ORDER BY level DESC"
        ).fetchall()
        return {r["domain"]: {"level": r["level"], "label": _EXPERTISE_LEVELS.get(r["level"], "unknown"),
                               "evidence": r["evidence_count"]}
                for r in rows}


def get_explanation_calibration(domain: str = "general") -> str:
    """Return recommended explanation level for a domain."""
    init_db()
    with _conn() as con:
        row = con.execute(
            "SELECT level FROM domain_expertise WHERE domain=?", (domain,)
        ).fetchone()
        level = row["level"] if row else 2

    hints = {
        1: "Explain from first principles. Use analogies. Avoid jargon.",
        2: "Standard technical explanation. Define specialized terms briefly.",
        3: "Use correct terminology. Skip basics. Focus on nuance.",
        4: "Peer-level discussion. Assume deep expertise. Be precise and terse.",
    }
    return hints.get(level, hints[2])


def get_mind_summary() -> dict:
    """Return a full summary of what the agent knows about the user's knowledge."""
    return {
        "domain_expertise": get_domain_expertise(),
        "active_misconceptions": get_active_misconceptions(),
    }


def proactive_misconception_warning(user_message: str) -> Optional[str]:
    """If the user's message contains a known misconception, return a warning.

    Returns None if no misconception detected.
    """
    for pattern, description in _MISCONCEPTION_PATTERNS:
        if re.search(pattern, user_message, re.IGNORECASE):
            return (
                f"⚠️ **Heads up before I answer**: {description}. "
                f"This is a common source of subtle bugs. Want me to explain why?"
            )
    return None
