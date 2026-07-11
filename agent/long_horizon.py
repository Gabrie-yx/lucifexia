"""agent/long_horizon.py — Long-horizon goal tracking and planning for Lucifex.

Maintains multi-month goals, decomposes them into milestones and tasks,
tracks progress each session, and projects real completion dates based on
current velocity. A weekly cron job writes progress reports to Obsidian.

The agent genuinely cares about your goals — if progress slips, it will
proactively reschedule, warn you, and suggest what to do today to get
back on track.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_lock = threading.RLock()
_db_path: Optional[Path] = None


def _get_db_path() -> Path:
    global _db_path
    if _db_path is None:
        try:
            from lucifex_constants import get_lucifex_home
            _db_path = Path(get_lucifex_home()) / "long_horizon.db"
        except Exception:
            _db_path = Path.home() / ".lucifex" / "long_horizon.db"
    return _db_path


@contextmanager
def _conn():
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
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS goals (
                id          TEXT PRIMARY KEY,
                title       TEXT NOT NULL,
                description TEXT,
                deadline    TEXT,
                progress    REAL DEFAULT 0.0,
                status      TEXT DEFAULT 'active',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS milestones (
                id          TEXT PRIMARY KEY,
                goal_id     TEXT NOT NULL,
                title       TEXT NOT NULL,
                due_date    TEXT,
                completed   INTEGER DEFAULT 0,
                created_at  TEXT NOT NULL,
                FOREIGN KEY (goal_id) REFERENCES goals(id)
            );

            CREATE TABLE IF NOT EXISTS progress_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id     TEXT NOT NULL,
                session_id  TEXT,
                delta       REAL DEFAULT 0.0,
                note        TEXT,
                logged_at   TEXT NOT NULL,
                FOREIGN KEY (goal_id) REFERENCES goals(id)
            );
        """)


# ── Goals ─────────────────────────────────────────────────────────────────────

def add_goal(
    title: str,
    description: str = "",
    deadline: Optional[str] = None,
    goal_id: Optional[str] = None,
) -> str:
    """Create a new long-horizon goal. Returns its ID."""
    import re
    init_db()
    if goal_id is None:
        goal_id = re.sub(r"\W+", "_", title.lower())[:40]
    now = _now()
    with _conn() as con:
        con.execute("""
            INSERT OR REPLACE INTO goals
            (id, title, description, deadline, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (goal_id, title, description, deadline, now, now))
    logger.info("Goal created: %s", title)
    return goal_id


def get_active_goals() -> list[dict]:
    init_db()
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM goals WHERE status='active' ORDER BY deadline ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_goal(goal_id: str) -> Optional[dict]:
    init_db()
    with _conn() as con:
        row = con.execute("SELECT * FROM goals WHERE id=?", (goal_id,)).fetchone()
        return dict(row) if row else None


def complete_goal(goal_id: str) -> None:
    init_db()
    with _conn() as con:
        con.execute(
            "UPDATE goals SET status='completed', progress=1.0, updated_at=? WHERE id=?",
            (_now(), goal_id),
        )


# ── Milestones ─────────────────────────────────────────────────────────────────

def add_milestone(goal_id: str, title: str, due_date: Optional[str] = None) -> str:
    import uuid
    init_db()
    mid = str(uuid.uuid4())[:8]
    with _conn() as con:
        con.execute(
            "INSERT INTO milestones (id, goal_id, title, due_date, created_at) VALUES (?,?,?,?,?)",
            (mid, goal_id, title, due_date, _now()),
        )
    return mid


def get_milestones(goal_id: str) -> list[dict]:
    init_db()
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM milestones WHERE goal_id=? ORDER BY due_date ASC",
            (goal_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def complete_milestone(milestone_id: str) -> None:
    init_db()
    with _conn() as con:
        con.execute(
            "UPDATE milestones SET completed=1 WHERE id=?", (milestone_id,)
        )
    # Recalculate parent goal progress
    with _conn() as con:
        row = con.execute(
            "SELECT goal_id FROM milestones WHERE id=?", (milestone_id,)
        ).fetchone()
        if row:
            _recalculate_progress(row["goal_id"], con)


def _recalculate_progress(goal_id: str, con) -> float:
    """Recalculate goal progress from milestone completion ratio."""
    total = con.execute(
        "SELECT COUNT(*) FROM milestones WHERE goal_id=?", (goal_id,)
    ).fetchone()[0]
    done = con.execute(
        "SELECT COUNT(*) FROM milestones WHERE goal_id=? AND completed=1", (goal_id,)
    ).fetchone()[0]
    progress = (done / total) if total > 0 else 0.0
    con.execute(
        "UPDATE goals SET progress=?, updated_at=? WHERE id=?",
        (progress, _now(), goal_id),
    )
    return progress


# ── Progress Tracking ─────────────────────────────────────────────────────────

def log_progress(
    goal_id: str,
    delta: float,
    session_id: str = "",
    note: str = "",
) -> None:
    """Log incremental progress (0.0–1.0 scale) for a goal."""
    init_db()
    with _conn() as con:
        con.execute(
            "INSERT INTO progress_log (goal_id, session_id, delta, note, logged_at) VALUES (?,?,?,?,?)",
            (goal_id, session_id, delta, note, _now()),
        )
        # Update cumulative progress (capped at 1.0)
        con.execute("""
            UPDATE goals SET
                progress = MIN(1.0, progress + ?),
                updated_at = ?
            WHERE id=?
        """, (delta, _now(), goal_id))


# ── Projection ────────────────────────────────────────────────────────────────

def project_completion(goal_id: str) -> dict:
    """Project the real completion date based on current velocity.

    Returns dict with: progress, velocity_per_day, projected_date, on_track, days_remaining.
    """
    init_db()
    goal = get_goal(goal_id)
    if not goal:
        return {"error": "goal not found"}

    with _conn() as con:
        # Get progress logs from last 14 days
        cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        logs = con.execute(
            "SELECT delta, logged_at FROM progress_log WHERE goal_id=? AND logged_at>? ORDER BY logged_at ASC",
            (goal_id, cutoff),
        ).fetchall()

    progress = float(goal.get("progress") or 0.0)
    remaining = 1.0 - progress

    if not logs:
        return {
            "goal": goal["title"],
            "progress": f"{progress:.0%}",
            "velocity_per_day": 0.0,
            "projected_date": None,
            "on_track": None,
            "message": "Not enough data to project — no progress logged in 14 days.",
        }

    total_delta = sum(float(r["delta"]) for r in logs)
    days_with_data = max(1, len(set(r["logged_at"][:10] for r in logs)))
    velocity = total_delta / days_with_data  # progress units per day

    if velocity <= 0:
        return {
            "goal": goal["title"],
            "progress": f"{progress:.0%}",
            "velocity_per_day": 0.0,
            "projected_date": None,
            "on_track": False,
            "message": "No recent progress detected. Goal is stalling.",
        }

    days_to_complete = remaining / velocity
    projected = datetime.now(timezone.utc) + timedelta(days=days_to_complete)

    on_track = None
    deadline_str = goal.get("deadline")
    if deadline_str:
        try:
            deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
            on_track = projected <= deadline
        except Exception:
            pass

    return {
        "goal": goal["title"],
        "progress": f"{progress:.0%}",
        "velocity_per_day": round(velocity, 4),
        "projected_date": projected.strftime("%Y-%m-%d"),
        "deadline": deadline_str[:10] if deadline_str else None,
        "on_track": on_track,
        "days_to_complete": round(days_to_complete),
        "message": (
            f"At current pace, you'll finish in ~{round(days_to_complete)} days "
            f"({'on track ✓' if on_track else 'BEHIND schedule ⚠' if on_track is False else 'no deadline set'})."
        ),
    }


# ── Decomposition ─────────────────────────────────────────────────────────────

def decompose_goal_with_ai(goal_id: str) -> list[str]:
    """Use a lightweight model call to break a goal into milestones."""
    goal = get_goal(goal_id)
    if not goal:
        return []

    try:
        from agent.oneshot import run_oneshot
        prompt = (
            f"Break this goal into 4-6 concrete milestones with clear completion criteria.\n\n"
            f"Goal: {goal['title']}\n"
            f"Description: {goal.get('description', '')}\n"
            f"Deadline: {goal.get('deadline', 'not set')}\n\n"
            f"Return ONLY a JSON array of milestone titles, e.g.:\n"
            f'["Milestone 1", "Milestone 2", ...]'
        )
        result = run_oneshot(prompt, max_tokens=300)
        import re
        match = re.search(r"\[.*\]", result, re.DOTALL)
        if match:
            milestones = json.loads(match.group())
            milestone_ids = []
            for title in milestones:
                mid = add_milestone(goal_id, title)
                milestone_ids.append(mid)
            logger.info("Decomposed goal '%s' into %d milestones", goal["title"], len(milestones))
            return milestone_ids
    except Exception as exc:
        logger.debug("Goal decomposition failed: %s", exc)
    return []


# ── Weekly Report ─────────────────────────────────────────────────────────────

def write_weekly_report_to_obsidian() -> Optional[str]:
    """Write a weekly progress report to Obsidian Goals/ folder."""
    try:
        goals = get_active_goals()
        if not goals:
            return None

        from tools.playbook_tool import _resolve_obsidian_vault_path
        vault = _resolve_obsidian_vault_path()
        goals_dir = vault / "Goals"
        goals_dir.mkdir(parents=True, exist_ok=True)

        week = datetime.now().strftime("%Y-W%W")
        lines = [
            f"---",
            f"title: Weekly Goal Progress — {week}",
            f"created: {_now()}",
            f"source: agent-long-horizon",
            f"---",
            f"",
            f"# Goal Progress — Week {week}",
            f"",
        ]

        for goal in goals:
            proj = project_completion(goal["id"])
            milestones = get_milestones(goal["id"])
            done_ms = sum(1 for m in milestones if m.get("completed"))
            lines += [
                f"## {goal['title']}",
                f"- **Progress:** {float(goal['progress']):.0%}",
                f"- **Milestones:** {done_ms}/{len(milestones)} completed",
                f"- **Projection:** {proj.get('message', 'N/A')}",
                f"",
            ]
            for ms in milestones:
                check = "x" if ms.get("completed") else " "
                lines.append(f"  - [{check}] {ms['title']}")
            lines.append("")

        content = "\n".join(lines)
        out = goals_dir / f"progress-{week}.md"
        out.write_text(content, encoding="utf-8")
        logger.info("Weekly progress report written: %s", out)
        return str(out)
    except Exception as exc:
        logger.debug("Failed to write weekly report: %s", exc)
        return None
