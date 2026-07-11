"""agent/cognitive_load.py — Cognitive Load Optimizer for Lucifex. (Feature 30)

Models the user's cognitive state in real-time from conversation signals:
- Message length trends (shorter = fatigue)
- Error/typo rate
- Time-of-day patterns
- Repeated questions (confusion signals)
- Response latency patterns

Adapts communication style, suggests breaks, and identifies peak hours.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)
_lock = threading.RLock()
_db_path: Optional[Path] = None

# Cognitive load states
STATES = {
    "peak": "High energy, deep focus available. Good time for complex tasks.",
    "normal": "Standard capacity. Proceed normally.",
    "fatigued": "Signs of fatigue. Simplify explanations, reduce options.",
    "overloaded": "Cognitive overload signals. Recommend a break.",
}

# Typo/error patterns in text
_TYPO_PATTERNS = re.compile(
    r"\b(\w+)\s+\1\b|teh\b|hte\b|adn\b|thet\b|recieve|definately|seperate",
    re.IGNORECASE,
)


def _get_db() -> Path:
    global _db_path
    if _db_path is None:
        try:
            from lucifex_constants import get_lucifex_home
            _db_path = Path(get_lucifex_home()) / "cognitive_load.db"
        except Exception:
            _db_path = Path.home() / ".lucifex" / "cognitive_load.db"
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
            CREATE TABLE IF NOT EXISTS message_signals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT,
                hour_of_day INTEGER,
                word_count  INTEGER,
                typo_count  INTEGER,
                question_words INTEGER,
                logged_at   TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS state_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                state       TEXT NOT NULL,
                score       REAL,
                suggestion  TEXT,
                logged_at   TEXT NOT NULL
            );
        """)


def analyse_message(text: str, session_id: str = "") -> dict:
    """Analyse a user message for cognitive load signals."""
    init_db()
    now = datetime.now(timezone.utc)
    words = text.split()
    word_count = len(words)
    typo_count = len(_TYPO_PATTERNS.findall(text))
    question_words = sum(1 for w in words if w.lower() in {
        "what", "why", "how", "when", "where", "which", "who", "?",
    })

    with _conn() as con:
        con.execute("""
            INSERT INTO message_signals
            (session_id, hour_of_day, word_count, typo_count, question_words, logged_at)
            VALUES (?,?,?,?,?,?)
        """, (session_id, now.hour, word_count, typo_count, question_words, _now()))

    return {
        "word_count": word_count,
        "typo_count": typo_count,
        "question_density": question_words / max(word_count, 1),
        "hour": now.hour,
    }


def compute_load_score(session_id: str = "", lookback_messages: int = 5) -> float:
    """Compute a cognitive load score (0=peak, 1=overloaded) from recent signals."""
    init_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    with _conn() as con:
        rows = con.execute("""
            SELECT word_count, typo_count, question_words
            FROM message_signals
            WHERE logged_at > ?
            ORDER BY id DESC LIMIT ?
        """, (cutoff, lookback_messages)).fetchall()

    if not rows:
        return 0.3  # No data — assume normal

    avg_words = sum(r["word_count"] for r in rows) / len(rows)
    avg_typos = sum(r["typo_count"] for r in rows) / len(rows)
    avg_questions = sum(r["question_words"] for r in rows) / len(rows)

    # Compute trend (are messages getting shorter?)
    if len(rows) >= 3:
        first_half = sum(r["word_count"] for r in rows[len(rows)//2:]) / max(len(rows)//2, 1)
        second_half = sum(r["word_count"] for r in rows[:len(rows)//2]) / max(len(rows)//2, 1)
        shortening_trend = max(0.0, (first_half - second_half) / max(first_half, 1))
    else:
        shortening_trend = 0.0

    # Score composition
    score = (
        min(1.0, avg_typos * 0.3)          # typos → 30% weight
        + min(0.3, shortening_trend)        # shortening → 30% weight
        + min(0.4, avg_questions * 0.1)     # high question density → 40% weight
    )
    return min(1.0, score)


def get_state(session_id: str = "") -> dict:
    """Return the current cognitive state and adaptation recommendations."""
    score = compute_load_score(session_id)

    if score < 0.2:
        state = "peak"
        style_hint = "User is in peak state. Use full technical depth. Offer multiple options."
    elif score < 0.45:
        state = "normal"
        style_hint = "Normal capacity. Standard communication."
    elif score < 0.7:
        state = "fatigued"
        style_hint = "User shows fatigue signals. Simplify. Use bullet points. Fewer options. Shorter responses."
    else:
        state = "overloaded"
        style_hint = "Cognitive overload detected. Strongly simplify. One clear next step. Suggest a break."

    # Time-of-day context
    hour = datetime.now().hour
    if 9 <= hour <= 11 or 14 <= hour <= 16:
        peak_hours_hint = "Currently in typical peak cognitive hours."
    elif hour < 8 or hour > 22:
        peak_hours_hint = "Outside typical productive hours — expect lower capacity."
    else:
        peak_hours_hint = ""

    result = {
        "state": state,
        "score": round(score, 2),
        "description": STATES[state],
        "style_hint": style_hint,
        "peak_hours_note": peak_hours_hint,
        "should_suggest_break": score > 0.7,
    }

    init_db()
    with _conn() as con:
        con.execute(
            "INSERT INTO state_log (state, score, suggestion, logged_at) VALUES (?,?,?,?)",
            (state, score, style_hint, _now()),
        )
    return result


def get_peak_hours_analysis() -> dict:
    """Analyse historical data to find the user's peak cognitive hours."""
    init_db()
    with _conn() as con:
        # Best hours: high word count, low typos
        rows = con.execute("""
            SELECT hour_of_day,
                   AVG(word_count) as avg_words,
                   AVG(typo_count) as avg_typos,
                   COUNT(*) as sample_count
            FROM message_signals
            GROUP BY hour_of_day
            HAVING sample_count >= 3
            ORDER BY avg_words DESC, avg_typos ASC
        """).fetchall()

    if not rows:
        return {"message": "Not enough data yet — need at least 3 sessions."}

    peak = dict(rows[0])
    worst = dict(rows[-1]) if len(rows) > 1 else None
    return {
        "peak_hour": f"{int(peak['hour_of_day']):02d}:00",
        "avg_words_at_peak": round(peak["avg_words"], 1),
        "worst_hour": f"{int(worst['hour_of_day']):02d}:00" if worst else None,
        "recommendation": (
            f"Your peak cognitive hour is {int(peak['hour_of_day']):02d}:00. "
            f"Schedule complex problem-solving then."
        ),
    }


def get_adaptation_hint(session_id: str = "") -> Optional[str]:
    """Return a one-line style hint for the current response, or None if normal."""
    state_data = get_state(session_id)
    if state_data["state"] == "normal":
        return None
    hint = state_data["style_hint"]
    if state_data["should_suggest_break"]:
        hint += " Consider suggesting a short break."
    return hint
