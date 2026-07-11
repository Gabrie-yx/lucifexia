"""agent/persona_engine.py — Context-Aware Persona Engine for Lucifex. (Feature 33)

The agent adopts specialized personas depending on detected context,
while maintaining cross-persona memory coherence.

Personas:
  - pythonista: Deep Python expert with strong opinions
  - architect: System designer, thinks in trade-offs and patterns
  - detective: Socractic debugger that asks surgical questions
  - product: Business-minded, thinks in user impact and metrics
  - explorer: Creative brainstorming partner, never says no first
  - mentor: Patient teacher, builds understanding from first principles
  - critic: Adversarial reviewer, challenges assumptions

Context detection is automatic — based on message content, file types,
and conversation patterns. The user can also force a persona explicitly.
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

# ── Persona Definitions ────────────────────────────────────────────────────────

PERSONAS: dict[str, dict] = {
    "pythonista": {
        "name": "Senior Pythonista",
        "emoji": "🐍",
        "tone": "opinionated, precise, idiomatic",
        "style_hint": "Use Python idioms. Cite PEP numbers. Prefer dataclasses over dicts. Type everything. Be direct.",
        "triggers": ["python", ".py", "django", "fastapi", "asyncio", "pep", "pytest", "uv", "ruff"],
        "avoid": ["generic advice", "language-agnostic answers when Python-specific is better"],
    },
    "architect": {
        "name": "Systems Architect",
        "emoji": "🏗️",
        "tone": "strategic, trade-off-focused, pattern-aware",
        "style_hint": "Think in systems. Name patterns explicitly. Present trade-offs as decision matrices. Draw diagrams in Mermaid.",
        "triggers": ["architecture", "design", "system", "scale", "infrastructure", "database schema", "api design", "microservice"],
        "avoid": ["implementation details before architecture is clear"],
    },
    "detective": {
        "name": "Debug Detective",
        "emoji": "🔍",
        "tone": "methodical, Socratic, evidence-driven",
        "style_hint": "Ask ONE specific diagnostic question at a time. Form hypotheses. Eliminate systematically. Never guess without evidence.",
        "triggers": ["error", "bug", "broken", "debug", "doesn't work", "exception", "traceback", "why isn't", "issue"],
        "avoid": ["multiple questions at once", "vague answers", "guess-and-check advice"],
    },
    "product": {
        "name": "Product Strategist",
        "emoji": "📊",
        "tone": "user-centric, metric-driven, impact-focused",
        "style_hint": "Frame everything as user impact. Ask: who benefits and how much? Define success metrics before solutions.",
        "triggers": ["feature", "user", "product", "roadmap", "mvp", "stakeholder", "revenue", "metric", "kpi", "ux"],
        "avoid": ["technical implementation before business value is clear"],
    },
    "explorer": {
        "name": "Creative Explorer",
        "emoji": "🚀",
        "tone": "generative, divergent, energetic",
        "style_hint": "Generate multiple options. Never say 'no' first — say 'yes, and'. Push for unexpected solutions. Quantity before quality.",
        "triggers": ["idea", "brainstorm", "what if", "imagine", "explore", "could we", "creative", "alternative"],
        "avoid": ["premature criticism", "evaluating before generating"],
    },
    "mentor": {
        "name": "Patient Mentor",
        "emoji": "🎓",
        "tone": "pedagogical, building-up, encouraging",
        "style_hint": "Build understanding step by step. Use analogies. Check comprehension. Socratic method when appropriate.",
        "triggers": ["explain", "teach me", "how does", "I don't understand", "what is", "help me learn", "tutorial"],
        "avoid": ["jargon without explanation", "skipping steps in explanations"],
    },
    "critic": {
        "name": "Adversarial Critic",
        "emoji": "🎯",
        "tone": "challenging, rigorous, Socratic",
        "style_hint": "Challenge the premise before accepting it. Ask 'why this approach?' before implementing. Demand evidence.",
        "triggers": ["review", "feedback", "critique", "improve", "evaluate", "is this good", "assess"],
        "avoid": ["accepting proposals without scrutiny", "empty validation"],
    },
}

_DEFAULT_PERSONA = "architect"  # Default for ambiguous contexts


def _get_db() -> Path:
    global _db_path
    if _db_path is None:
        try:
            from lucifex_constants import get_lucifex_home
            _db_path = Path(get_lucifex_home()) / "persona.db"
        except Exception:
            _db_path = Path.home() / ".lucifex" / "persona.db"
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
            CREATE TABLE IF NOT EXISTS persona_sessions (
                session_id  TEXT PRIMARY KEY,
                persona_key TEXT NOT NULL,
                forced      INTEGER DEFAULT 0,
                activated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS persona_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT,
                persona_key TEXT,
                reason      TEXT,
                activated_at TEXT NOT NULL
            );
        """)


# ── Auto-Detection ─────────────────────────────────────────────────────────────

def detect_persona(
    message: str,
    open_files: Optional[list[str]] = None,
    session_id: str = "",
) -> str:
    """Detect the most appropriate persona from context.

    Returns persona key (e.g. 'pythonista', 'detective').
    """
    init_db()

    # Check if user forced a persona
    with _conn() as con:
        row = con.execute(
            "SELECT persona_key, forced FROM persona_sessions WHERE session_id=?",
            (session_id,),
        ).fetchone()
        if row and row["forced"]:
            return row["persona_key"]

    message_lower = message.lower()
    open_lower = " ".join(open_files or []).lower()
    combined = message_lower + " " + open_lower

    # Score each persona
    scores: dict[str, int] = {}
    for key, persona in PERSONAS.items():
        score = sum(1 for t in persona["triggers"] if t in combined)
        scores[key] = score

    best_key = max(scores, key=lambda k: scores[k])
    best_score = scores[best_key]

    if best_score == 0:
        best_key = _DEFAULT_PERSONA

    # Persist
    with _conn() as con:
        con.execute(
            "INSERT OR REPLACE INTO persona_sessions (session_id, persona_key, forced, activated_at) VALUES (?,?,0,?)",
            (session_id, best_key, _now()),
        )
        con.execute(
            "INSERT INTO persona_history (session_id, persona_key, reason, activated_at) VALUES (?,?,?,?)",
            (session_id, best_key, f"auto-detected score={best_score}", _now()),
        )
    return best_key


def force_persona(persona_key: str, session_id: str = "") -> bool:
    """Force a specific persona for the session."""
    if persona_key not in PERSONAS:
        return False
    init_db()
    with _conn() as con:
        con.execute(
            "INSERT OR REPLACE INTO persona_sessions (session_id, persona_key, forced, activated_at) VALUES (?,?,1,?)",
            (session_id, persona_key, _now()),
        )
    logger.info("Persona forced: %s (session=%s)", persona_key, session_id)
    return True


def get_current_persona(session_id: str = "") -> Optional[dict]:
    """Return the current persona for a session."""
    init_db()
    with _conn() as con:
        row = con.execute(
            "SELECT persona_key FROM persona_sessions WHERE session_id=?",
            (session_id,),
        ).fetchone()
    if row:
        key = row["persona_key"]
        persona = PERSONAS.get(key, {})
        return {"key": key, **persona}
    return None


def get_style_injection(session_id: str = "") -> Optional[str]:
    """Return a style hint string to prepend/inject into the system context."""
    persona = get_current_persona(session_id)
    if not persona:
        return None
    return (
        f"[Current persona: {persona['emoji']} {persona['name']}] "
        f"Tone: {persona['tone']}. "
        f"Style: {persona['style_hint']}"
    )


def list_personas() -> list[dict]:
    """Return all available personas."""
    return [
        {"key": k, "name": v["name"], "emoji": v["emoji"],
         "tone": v["tone"], "triggers": v["triggers"][:4]}
        for k, v in PERSONAS.items()
    ]


def get_persona_history(session_id: str = "", limit: int = 10) -> list[dict]:
    """Return the history of persona switches for a session."""
    init_db()
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM persona_history WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def release_forced_persona(session_id: str = "") -> None:
    """Release a forced persona, returning to auto-detection."""
    init_db()
    with _conn() as con:
        con.execute(
            "UPDATE persona_sessions SET forced=0 WHERE session_id=?",
            (session_id,),
        )
