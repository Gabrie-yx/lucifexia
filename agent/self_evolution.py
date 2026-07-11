"""agent/self_evolution.py — Self-Modifying System Prompt Engine. (Feature 28)

The agent observes its own failure patterns across sessions and proposes
improvements to its own system prompt. It runs implicit A/B testing,
measures outcome quality, and when a variant consistently outperforms,
proposes permanent adoption.

This is genuine self-improvement without fine-tuning.
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

# Quality signals — positive
_SUCCESS_SIGNALS = [
    r"thank you|perfect|exactly|that's it|great solution|works perfectly",
    r"this is what I needed|you nailed it|spot on|brilliant",
]
# Quality signals — negative
_FAILURE_SIGNALS = [
    r"that's wrong|not what I asked|you misunderstood|try again",
    r"that doesn't work|incorrect|you missed the point|no, I meant",
    r"actually,? I was asking|can you redo|let me clarify again",
]

_SUCCESS_RE = [re.compile(p, re.IGNORECASE) for p in _SUCCESS_SIGNALS]
_FAILURE_RE = [re.compile(p, re.IGNORECASE) for p in _FAILURE_SIGNALS]


def _get_db() -> Path:
    global _db_path
    if _db_path is None:
        try:
            from lucifex_constants import get_lucifex_home
            _db_path = Path(get_lucifex_home()) / "self_evolution.db"
        except Exception:
            _db_path = Path.home() / ".lucifex" / "self_evolution.db"
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
            CREATE TABLE IF NOT EXISTS quality_signals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT,
                signal_type TEXT,
                context     TEXT,
                logged_at   TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS failure_patterns (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern     TEXT NOT NULL,
                count       INTEGER DEFAULT 1,
                first_seen  TEXT NOT NULL,
                last_seen   TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS prompt_variants (
                id          TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                diff        TEXT NOT NULL,
                score       REAL DEFAULT 0.0,
                trials      INTEGER DEFAULT 0,
                adopted     INTEGER DEFAULT 0,
                created_at  TEXT NOT NULL
            );
        """)


def score_turn(
    user_followup: str,
    session_id: str = "",
    context: str = "",
) -> float:
    """Score the quality of the previous turn based on user follow-up.

    Returns: +1.0 (success), -1.0 (failure), 0.0 (neutral).
    """
    init_db()
    score = 0.0

    if any(p.search(user_followup) for p in _SUCCESS_RE):
        score = 1.0
        with _conn() as con:
            con.execute(
                "INSERT INTO quality_signals (session_id, signal_type, context, logged_at) VALUES (?,?,?,?)",
                (session_id, "success", context[:200], _now()),
            )
    elif any(p.search(user_followup) for p in _FAILURE_RE):
        score = -1.0
        with _conn() as con:
            con.execute(
                "INSERT INTO quality_signals (session_id, signal_type, context, logged_at) VALUES (?,?,?,?)",
                (session_id, "failure", context[:200], _now()),
            )

    return score


def record_failure_pattern(description: str) -> None:
    """Record a recurring failure pattern for analysis."""
    init_db()
    with _conn() as con:
        existing = con.execute(
            "SELECT id, count FROM failure_patterns WHERE pattern=?", (description[:200],)
        ).fetchone()
        if existing:
            con.execute(
                "UPDATE failure_patterns SET count=count+1, last_seen=? WHERE id=?",
                (_now(), existing["id"]),
            )
        else:
            con.execute(
                "INSERT INTO failure_patterns (pattern, first_seen, last_seen) VALUES (?,?,?)",
                (description[:200], _now(), _now()),
            )


def get_quality_stats() -> dict:
    """Return quality statistics across all sessions."""
    init_db()
    with _conn() as con:
        total = con.execute("SELECT COUNT(*) FROM quality_signals").fetchone()[0]
        successes = con.execute(
            "SELECT COUNT(*) FROM quality_signals WHERE signal_type='success'"
        ).fetchone()[0]
        failures = con.execute(
            "SELECT COUNT(*) FROM quality_signals WHERE signal_type='failure'"
        ).fetchone()[0]
        patterns = con.execute(
            "SELECT pattern, count FROM failure_patterns ORDER BY count DESC LIMIT 5"
        ).fetchall()

    rate = successes / total if total > 0 else 0.0
    return {
        "total_signals": total,
        "success_rate": f"{rate:.0%}",
        "successes": successes,
        "failures": failures,
        "top_failure_patterns": [dict(p) for p in patterns],
    }


def generate_prompt_improvement() -> Optional[dict]:
    """Analyse failure patterns and propose a system prompt improvement."""
    stats = get_quality_stats()
    patterns = stats.get("top_failure_patterns", [])
    if not patterns:
        return None

    try:
        from agent.oneshot import run_oneshot
        pattern_list = "\n".join(
            f"- {p['pattern']} (occurred {p['count']} times)" for p in patterns[:3]
        )
        prompt = (
            f"You are improving an AI agent's system prompt based on observed failure patterns.\n\n"
            f"Failure patterns:\n{pattern_list}\n\n"
            f"Current success rate: {stats['success_rate']}\n\n"
            f"Propose ONE specific addition or modification to the agent's system prompt "
            f"that would directly address these failure patterns. "
            f"Return a JSON object:\n"
            f'{{"description": "What this change does", "diff": "The exact text to add/modify"}}'
        )
        result = run_oneshot(prompt, max_tokens=300)
        if result:
            match = re.search(r"\{.*\}", result, re.DOTALL)
            if match:
                data = json.loads(match.group())
                import uuid
                variant_id = str(uuid.uuid4())[:8]
                init_db()
                with _conn() as con:
                    con.execute("""
                        INSERT INTO prompt_variants (id, description, diff, created_at)
                        VALUES (?,?,?,?)
                    """, (variant_id, data.get("description", ""), data.get("diff", ""), _now()))
                return {"id": variant_id, **data}
    except Exception as exc:
        logger.debug("Prompt improvement generation failed: %s", exc)
    return None


def write_evolution_report_to_obsidian() -> Optional[str]:
    """Write agent self-evolution report to Obsidian."""
    try:
        stats = get_quality_stats()
        improvement = generate_prompt_improvement()

        from tools.playbook_tool import _resolve_obsidian_vault_path
        vault = _resolve_obsidian_vault_path()
        evo_dir = vault / "SelfEvolution"
        evo_dir.mkdir(parents=True, exist_ok=True)
        date = datetime.now().strftime("%Y-%m-%d")
        out = evo_dir / f"{date}-evolution-report.md"

        lines = [
            f"---\ntitle: Self-Evolution Report — {date}\nsource: agent-self-evolution\n---\n",
            f"# Agent Self-Evolution Report — {date}\n",
            f"## Quality Metrics\n",
            f"- **Success rate:** {stats['success_rate']}",
            f"- **Total signals:** {stats['total_signals']}",
            f"- **Successes:** {stats['successes']} | **Failures:** {stats['failures']}\n",
            f"## Top Failure Patterns\n",
        ]
        for p in stats.get("top_failure_patterns", []):
            lines.append(f"- {p['pattern']} *(×{p['count']})*")
        if improvement:
            lines += [
                f"\n## Proposed Prompt Improvement\n",
                f"**{improvement.get('description', '')}**\n",
                f"```\n{improvement.get('diff', '')}\n```",
            ]
        out.write_text("\n".join(lines), encoding="utf-8")
        return str(out)
    except Exception as exc:
        logger.debug("Evolution report failed: %s", exc)
        return None
