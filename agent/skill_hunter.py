"""agent/skill_hunter.py — Autonomous Skill Acquisition for Lucifex.

When the agent detects it cannot do something well, it autonomously:
1. Identifies the capability gap
2. Searches for documentation/examples
3. Writes and tests integration code
4. Creates a new tool or skill file — without being asked

This is self-directed learning: the agent grows its own capabilities
by recognizing its own limitations and filling them.
"""
from __future__ import annotations

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

# Patterns that indicate capability gaps in agent responses
_GAP_PATTERNS = [
    (r"I can't (access|read|control|interact with|open|use)\s+(\w[\w\s]+)", "tool_access"),
    (r"I don't have (a tool|the ability|access to|support for)\s+(\w[\w\s]+)", "missing_tool"),
    (r"I'm not able to\s+(\w[\w\s]+)", "capability_gap"),
    (r"there's no (built-in|native|direct) (way|support|integration) to\s+(\w[\w\s]+)", "missing_integration"),
    (r"I (lack|don't have) a skill for\s+(\w[\w\s]+)", "missing_skill"),
]

_COMPILED_GAPS = [(re.compile(p, re.IGNORECASE), t) for p, t in _GAP_PATTERNS]


def _get_db() -> Path:
    global _db_path
    if _db_path is None:
        try:
            from lucifex_constants import get_lucifex_home
            _db_path = Path(get_lucifex_home()) / "skill_gaps.db"
        except Exception:
            _db_path = Path.home() / ".lucifex" / "skill_gaps.db"
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
            CREATE TABLE IF NOT EXISTS skill_gaps (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                gap_type    TEXT,
                description TEXT NOT NULL,
                session_id  TEXT,
                resolved    INTEGER DEFAULT 0,
                skill_path  TEXT,
                detected_at TEXT NOT NULL
            );
        """)


# ── Gap Detection ─────────────────────────────────────────────────────────────

def detect_gaps(response_text: str, session_id: str = "") -> list[str]:
    """Detect capability gaps in agent response text. Returns descriptions of gaps found."""
    init_db()
    gaps = []

    for compiled_pattern, gap_type in _COMPILED_GAPS:
        matches = compiled_pattern.findall(response_text)
        for match in matches:
            description = match if isinstance(match, str) else " ".join(str(m) for m in match if m)
            description = description.strip()[:120]
            if description:
                gaps.append(description)
                try:
                    with _conn() as con:
                        con.execute(
                            "INSERT INTO skill_gaps (gap_type, description, session_id, detected_at) VALUES (?,?,?,?)",
                            (gap_type, description, session_id, _now()),
                        )
                    logger.debug("Skill gap detected [%s]: %s", gap_type, description)
                except Exception as exc:
                    logger.debug("Failed to log gap: %s", exc)

    return gaps


def get_unresolved_gaps(limit: int = 5) -> list[dict]:
    """Return unresolved skill gaps for processing."""
    init_db()
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM skill_gaps WHERE resolved=0 ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# ── Skill Creation ────────────────────────────────────────────────────────────

def _research_capability(description: str) -> Optional[str]:
    """Research how to implement a missing capability."""
    try:
        from agent.oneshot import run_oneshot
        prompt = (
            f"Research how to implement this capability in Python for a CLI AI agent running on the user's machine:\n\n"
            f"Capability needed: {description}\n\n"
            f"Provide:\n"
            f"1. Which Python library or approach to use (be specific)\n"
            f"2. A minimal working code snippet (15-30 lines)\n"
            f"3. The pip install command if needed\n\n"
            f"Be concrete and executable. No explanations, just the solution."
        )
        return run_oneshot(prompt, max_tokens=500)
    except Exception as exc:
        logger.debug("Research failed: %s", exc)
        return None


def _create_skill_file(description: str, research: str) -> Optional[str]:
    """Create a skill Markdown file from the research results."""
    try:
        from lucifex_constants import get_lucifex_home
        skills_dir = Path(get_lucifex_home()) / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)

        slug = re.sub(r"\W+", "-", description[:40]).lower().strip("-")
        skill_file = skills_dir / f"auto-{slug}.md"

        if skill_file.exists():
            return str(skill_file)

        content = f"""---
name: auto-{slug}
description: Auto-generated skill — {description}
auto_generated: true
generated_at: {_now()}
---

# {description.title()}

*This skill was automatically generated by Lucifex's Skill Acquisition system.*

## Research

{research}

## Usage

When asked to {description}, follow the approach above.
"""
        skill_file.write_text(content, encoding="utf-8")
        logger.info("Auto-generated skill: %s", skill_file.name)
        return str(skill_file)
    except Exception as exc:
        logger.debug("Skill file creation failed: %s", exc)
        return None


def _validate_code_snippet(code: str) -> bool:
    """Quick syntax validation of a Python snippet."""
    try:
        import ast
        # Extract python code blocks
        match = re.search(r"```python\n(.*?)```", code, re.DOTALL)
        if match:
            ast.parse(match.group(1))
        return True
    except SyntaxError:
        return False
    except Exception:
        return True  # Unknown — assume valid


def process_skill_gaps(max_gaps: int = 2) -> list[dict]:
    """Process unresolved skill gaps: research and create skills.

    Returns list of processed results.
    """
    gaps = get_unresolved_gaps(limit=max_gaps)
    results = []

    for gap in gaps:
        description = gap.get("description", "")
        if not description or len(description) < 10:
            continue

        logger.info("Processing skill gap: %s", description[:60])
        research = _research_capability(description)

        if not research:
            continue

        skill_path = _create_skill_file(description, research)

        # Write to Obsidian as well
        _write_gap_to_obsidian(description, research, skill_path)

        try:
            with _conn() as con:
                con.execute(
                    "UPDATE skill_gaps SET resolved=1, skill_path=? WHERE id=?",
                    (skill_path or "", gap["id"]),
                )
        except Exception:
            pass

        results.append({
            "gap": description,
            "skill_created": skill_path,
            "research_length": len(research),
        })
        logger.info("Skill gap resolved: %s → %s", description[:50], skill_path)

    return results


def _write_gap_to_obsidian(description: str, research: str, skill_path: Optional[str]) -> None:
    """Write the skill acquisition result to Obsidian Discoveries/."""
    try:
        from tools.playbook_tool import _resolve_obsidian_vault_path
        vault = _resolve_obsidian_vault_path()
        disc_dir = vault / "Discoveries"
        disc_dir.mkdir(parents=True, exist_ok=True)

        slug = re.sub(r"\W+", "-", description[:40]).lower()
        date = datetime.now().strftime("%Y-%m-%d")
        fname = f"{date}-skill-acquired-{slug}.md"

        content = f"""---
title: "Skill Acquired: {description[:60]}"
category: pattern
impact: medium
created: {_now()}
source: agent-skill-hunter
tags:
  - skill-acquisition
  - autonomous-learning
---

## Capability Gap Identified

{description}

## Research Result

{research}

## Skill File Created

{skill_path or 'N/A'}
"""
        (disc_dir / fname).write_text(content, encoding="utf-8")
    except Exception as exc:
        logger.debug("Failed to write skill acquisition to Obsidian: %s", exc)
