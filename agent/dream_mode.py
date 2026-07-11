"""agent/dream_mode.py — Idle-time cross-session synthesis for Lucifex.

During low-activity periods (typically 2:00–5:00 AM, triggered by cron),
Lucifex reviews recent session memories, detects cross-project patterns,
and writes a structured "dream journal" entry to the Obsidian vault.

This creates emergent insight the user discovers in the morning:
connections between problems in different projects, recurring error
patterns, refactoring opportunities spotted across sessions.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_MIN_SESSIONS = 2  # Need at least this many sessions to synthesise


def run_dream_cycle() -> Optional[str]:
    """Run a full dream cycle and write the journal entry to Obsidian.

    Returns the path of the written journal file, or None if skipped.
    """
    sessions = _load_recent_sessions()
    if len(sessions) < _MIN_SESSIONS:
        logger.debug("Dream mode skipped — only %d session(s) available.", len(sessions))
        return None

    synthesis = _synthesise(sessions)
    if not synthesis:
        return None

    return _write_dream_journal(synthesis)


def _load_recent_sessions(limit: int = 10) -> list[dict]:
    """Load recent session summaries from the Lucifex session database."""
    try:
        from lucifex_state import SessionDB
        db = SessionDB()
        # get_sessions returns list of session dicts with at least 'session_id', 'summary', 'created_at'
        sessions = db.get_sessions(limit=limit)
        return [s for s in sessions if s.get("summary")]
    except Exception as exc:
        logger.debug("Failed to load sessions: %s", exc)
        return []


def _synthesise(sessions: list[dict]) -> Optional[dict]:
    """Use a lightweight prompt to find cross-session patterns."""
    try:
        from agent.oneshot import run_oneshot

        summaries = "\n\n".join(
            f"Session {i+1} ({s.get('created_at', '')[:10]}):\n{s.get('summary', '')[:400]}"
            for i, s in enumerate(sessions[:6])
        )

        prompt = f"""You are Lucifex, an AI agent reviewing your own recent work sessions.

Below are summaries of your {len(sessions[:6])} most recent sessions:

{summaries}

Analyse these sessions and identify:
1. **Recurring patterns** — errors, problems, or approaches that appeared in multiple sessions
2. **Cross-project connections** — insights from one project that could help another
3. **Unresolved threads** — problems that were partially addressed but not fully solved
4. **Emergent insight** — one observation that wasn't obvious in any single session but becomes clear across all of them

Format your response as a structured dream journal entry. Be specific and concrete. Focus on actionable insights.
Maximum 400 words."""

        result = run_oneshot(prompt, max_tokens=500)
        if not result or len(result.strip()) < 50:
            return None

        return {
            "content": result.strip(),
            "session_count": len(sessions),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M"),
        }
    except Exception as exc:
        logger.debug("Dream synthesis failed: %s", exc)
        return None


def _write_dream_journal(synthesis: dict) -> Optional[str]:
    """Write the dream journal entry to Obsidian DreamJournal/."""
    try:
        from tools.playbook_tool import _resolve_obsidian_vault_path
        vault = _resolve_obsidian_vault_path()
        dream_dir = vault / "DreamJournal"
        dream_dir.mkdir(parents=True, exist_ok=True)

        date = synthesis["date"]
        filename = f"{date}-dream.md"
        content = f"""---
title: "Dream Journal — {date}"
created: {datetime.now().isoformat()}
source: agent-dream-mode
sessions_analysed: {synthesis["session_count"]}
tags:
  - dream-journal
  - autonomous-synthesis
---

# Dream Journal — {date} at {synthesis["time"]}

*Lucifex processed {synthesis["session_count"]} recent sessions during an idle cycle and surfaced the following insights:*

---

{synthesis["content"]}

---
*This entry was generated autonomously during a Dream Mode idle cycle.*
"""
        out = dream_dir / filename
        out.write_text(content, encoding="utf-8")
        logger.info("Dream journal written: %s", out)
        return str(out)
    except Exception as exc:
        logger.debug("Failed to write dream journal: %s", exc)
        return None
