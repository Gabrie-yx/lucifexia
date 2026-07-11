"""agent/commitment_tracker.py — Contradiction Detector & Commitment Tracker. (Feature 29)

Maintains a structured log of every decision, promise, and technical
choice made across sessions. When the user says something that contradicts
a prior commitment, the agent flags it immediately.

Distinguishes contradictions from deliberate evolution:
- Hard contradiction: same context, opposite decision
- Soft evolution: new information justifies a changed decision

All commitments stored in SQLite with FTS for fast retrieval.
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

# Patterns that signal a commitment being made
_COMMITMENT_PATTERNS = [
    (r"we (will|should|must|need to|are going to)\s+(.{10,80})", "decision"),
    (r"I('ll| will| promise to| commit to)\s+(.{10,80})", "promise"),
    (r"let's (use|go with|adopt|stick with|avoid)\s+(.{10,80})", "technical_choice"),
    (r"we (won't|shouldn't|can't|don't|never)\s+(.{10,80})", "constraint"),
    (r"the (architecture|design|approach|plan) (is|will be|should be)\s+(.{10,80})", "architecture"),
    (r"decided (to|that|against)\s+(.{10,80})", "decision"),
]
_COMMITMENT_RE = [(re.compile(p, re.IGNORECASE), t) for p, t in _COMMITMENT_PATTERNS]


def _get_db() -> Path:
    global _db_path
    if _db_path is None:
        try:
            from lucifex_constants import get_lucifex_home
            _db_path = Path(get_lucifex_home()) / "commitments.db"
        except Exception:
            _db_path = Path.home() / ".lucifex" / "commitments.db"
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
            CREATE TABLE IF NOT EXISTS commitments (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT,
                text        TEXT NOT NULL,
                commit_type TEXT,
                context     TEXT,
                superseded  INTEGER DEFAULT 0,
                superseded_by INTEGER,
                created_at  TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS commitments_fts
            USING fts5(id UNINDEXED, text, commit_type, context);
        """)


def extract_and_store_commitments(text: str, session_id: str = "", context: str = "") -> int:
    """Extract commitments from text and store them. Returns count stored."""
    init_db()
    stored = 0
    for pattern, commit_type in _COMMITMENT_RE:
        for match in pattern.finditer(text):
            commitment_text = match.group().strip()[:200]
            if len(commitment_text) < 15:
                continue
            with _conn() as con:
                cur = con.execute("""
                    INSERT INTO commitments (session_id, text, commit_type, context, created_at)
                    VALUES (?,?,?,?,?)
                """, (session_id, commitment_text, commit_type, context[:200], _now()))
                row_id = cur.lastrowid
                con.execute("""
                    INSERT INTO commitments_fts(id, text, commit_type, context)
                    VALUES (?,?,?,?)
                """, (row_id, commitment_text, commit_type, context[:200]))
            stored += 1
    return stored


def find_contradictions(new_text: str, session_id: str = "") -> list[dict]:
    """Check if new_text contradicts any stored commitments.

    Returns list of contradiction dicts with: commitment, new_statement, severity.
    """
    init_db()
    contradictions = []

    # Extract key terms from new text
    keywords = [w for w in re.findall(r"\b\w{4,}\b", new_text) if w not in _STOPWORDS][:10]
    if not keywords:
        return []

    # Search for related prior commitments
    try:
        query = " OR ".join(keywords[:5])
        with _conn() as con:
            rows = con.execute("""
                SELECT c.* FROM commitments c
                JOIN commitments_fts f ON c.id = f.id
                WHERE commitments_fts MATCH ? AND c.superseded=0
                ORDER BY c.id DESC LIMIT 10
            """, (query,)).fetchall()
    except Exception:
        with _conn() as con:
            pattern = f"%{'%'.join(keywords[:3])}%"
            rows = con.execute(
                "SELECT * FROM commitments WHERE text LIKE ? AND superseded=0 ORDER BY id DESC LIMIT 10",
                (f"%{keywords[0]}%",),
            ).fetchall()

    for row in rows:
        prior = dict(row)
        severity = _detect_contradiction_severity(prior["text"], new_text)
        if severity > 0.5:
            contradictions.append({
                "commitment": prior["text"],
                "commitment_type": prior["commit_type"],
                "commitment_date": prior["created_at"][:10],
                "new_statement": new_text[:150],
                "severity": severity,
                "commitment_id": prior["id"],
            })

    return contradictions


def _detect_contradiction_severity(prior: str, current: str) -> float:
    """Heuristic: detect if current contradicts prior. Returns 0.0–1.0."""
    # Negation pairs
    negation_pairs = [
        (r"\bwill\b", r"\bwon't\b"), (r"\buse\b", r"\bavoid\b"),
        (r"\badopt\b", r"\breject\b"), (r"\bshould\b", r"\bshouldn't\b"),
        (r"\bgo with\b", r"\bstick with(?!out)\b"), (r"\binclude\b", r"\bexclude\b"),
    ]
    prior_l = prior.lower()
    current_l = current.lower()
    for pos, neg in negation_pairs:
        if re.search(pos, prior_l) and re.search(neg, current_l):
            return 0.8
        if re.search(neg, prior_l) and re.search(pos, current_l):
            return 0.8

    # Technology switches
    tech_keywords = _extract_tech_keywords(prior)
    current_tech = _extract_tech_keywords(current)
    if tech_keywords and current_tech and tech_keywords.isdisjoint(current_tech):
        if len(tech_keywords) > 0 and len(current_tech) > 0:
            return 0.65

    return 0.0


def _extract_tech_keywords(text: str) -> set:
    techs = {
        "postgres", "mysql", "mongodb", "redis", "sqlite", "kafka", "rabbitmq",
        "docker", "kubernetes", "react", "vue", "angular", "fastapi", "django",
        "flask", "graphql", "rest", "grpc", "typescript", "javascript", "python",
    }
    words = set(w.lower() for w in re.findall(r"\b\w+\b", text))
    return words & techs


_STOPWORDS = {
    "this", "that", "with", "from", "have", "will", "been", "were",
    "they", "them", "their", "what", "when", "where", "which", "would",
    "should", "could", "does", "done", "make", "made", "take", "like",
}


def supersede_commitment(commitment_id: int, reason: str = "") -> None:
    """Mark a commitment as superseded (intentionally changed)."""
    init_db()
    with _conn() as con:
        con.execute(
            "UPDATE commitments SET superseded=1 WHERE id=?", (commitment_id,)
        )


def get_active_commitments(limit: int = 20) -> list[dict]:
    """Return all active (non-superseded) commitments."""
    init_db()
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM commitments WHERE superseded=0 ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def format_contradiction_warning(contradictions: list[dict]) -> Optional[str]:
    """Format contradiction warnings as a user-visible message."""
    if not contradictions:
        return None
    lines = ["⚡ **Commitment Conflict Detected**\n"]
    for c in contradictions[:2]:
        date = c.get("commitment_date", "?")
        lines += [
            f"- **Previously decided ({date}):** *{c['commitment']}*",
            f"  **Now saying:** *{c['new_statement'][:100]}*",
            f"  ↳ Severity: {c['severity']:.0%} — Is this an intentional change or a contradiction?",
            "",
        ]
    return "\n".join(lines)
