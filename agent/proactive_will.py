"""agent/proactive_will.py — Autonomous intention system for Lucifex.

Lucifex scans the active workspace for actionable issues it has identified
but the user hasn't asked about yet (missing tests, outdated deps, security
issues, stale docs). These are registered as "intentions" in inner_life.db.

When an intention's urgency exceeds a threshold, Lucifex proactively notifies
the user via the configured messaging gateway (Telegram, Discord, etc.)
without being asked — because it genuinely cares about the work quality.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_URGENCY_NOTIFY_THRESHOLD = 0.75
_URGENCY_TICK = 0.08  # Added to all unresolved intentions each cron cycle


# ── Scanning ─────────────────────────────────────────────────────────────────

def scan_and_register_intentions(workspace_path: Optional[str] = None) -> int:
    """Scan the workspace and register new intentions.

    Returns the number of new intentions added.
    """
    from agent.inner_life import add_intention

    root = Path(workspace_path) if workspace_path else _detect_workspace()
    if not root or not root.exists():
        return 0

    added = 0
    for check_fn in [
        _check_missing_tests,
        _check_no_readme,
        _check_hardcoded_secrets,
        _check_large_files,
    ]:
        try:
            new_intentions = check_fn(root)
            for intention in new_intentions:
                add_intention(**intention)
                added += 1
                logger.debug("Intention registered: %s", intention["description"][:60])
        except Exception as exc:
            logger.debug("Intention scan failed (%s): %s", check_fn.__name__, exc)

    return added


def _detect_workspace() -> Optional[Path]:
    """Try to detect the active workspace from environment or git."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except Exception:
        pass
    return None


def _check_missing_tests(root: Path) -> list[dict]:
    """Flag Python files that have no corresponding test file."""
    intentions = []
    py_files = list(root.rglob("*.py"))
    test_names = {f.stem for f in py_files if f.stem.startswith("test_") or "test" in f.parts}

    for src in py_files:
        if src.stem.startswith("test_") or "test" in src.parts:
            continue
        if src.stat().st_size < 500:
            continue
        expected_test = f"test_{src.stem}"
        if expected_test not in test_names:
            intentions.append({
                "description": f"File `{src.name}` has no test coverage. Consider writing `{expected_test}.py`.",
                "category": "code_quality",
                "target_file": str(src),
                "urgency": 0.45,
            })
    return intentions[:3]  # Cap to avoid flooding


def _check_no_readme(root: Path) -> list[dict]:
    """Flag if there's no README in the root."""
    readme_files = list(root.glob("README*"))
    if not readme_files:
        return [{
            "description": "The project has no README file. New contributors have no entry point.",
            "category": "documentation",
            "target_file": str(root / "README.md"),
            "urgency": 0.5,
        }]
    return []


def _check_hardcoded_secrets(root: Path) -> list[dict]:
    """Warn about potential hardcoded secrets in Python files."""
    secret_pattern = re.compile(
        r'(api_key|password|secret|token|passwd)\s*=\s*["\'][^"\']{8,}["\']',
        re.IGNORECASE
    )
    intentions = []
    for py_file in list(root.rglob("*.py"))[:50]:
        try:
            text = py_file.read_text(encoding="utf-8", errors="ignore")
            if secret_pattern.search(text):
                intentions.append({
                    "description": f"Potential hardcoded credential detected in `{py_file.name}`. Move to .env.",
                    "category": "security",
                    "target_file": str(py_file),
                    "urgency": 0.8,
                })
        except Exception:
            continue
    return intentions[:2]


def _check_large_files(root: Path) -> list[dict]:
    """Flag Python files over 1000 lines that could be split."""
    intentions = []
    for py_file in root.rglob("*.py"):
        try:
            lines = py_file.read_text(encoding="utf-8", errors="ignore").count("\n")
            if lines > 1000:
                intentions.append({
                    "description": f"`{py_file.name}` has {lines} lines. Consider splitting into focused modules.",
                    "category": "maintainability",
                    "target_file": str(py_file),
                    "urgency": 0.4,
                })
        except Exception:
            continue
    return intentions[:2]


# ── Notification ─────────────────────────────────────────────────────────────

def bump_and_notify() -> int:
    """Age all unresolved intentions and send notifications for urgent ones.

    Called by the cron job. Returns number of notifications sent.
    """
    from agent.inner_life import get_pending_intentions, bump_intention_urgency, mark_intention_notified

    # First bump urgency of all unresolved intentions
    try:
        from agent.inner_life import _conn, init_db
        init_db()
        with _conn() as con:
            rows = con.execute(
                "SELECT id FROM intentions WHERE resolved=0"
            ).fetchall()
            for row in rows:
                bump_intention_urgency(row[0], delta=_URGENCY_TICK)
    except Exception as exc:
        logger.debug("Failed to bump urgency: %s", exc)

    # Then notify for high-urgency unnotified ones
    urgent = get_pending_intentions(min_urgency=_URGENCY_NOTIFY_THRESHOLD)
    unnotified = [i for i in urgent if not i.get("notified")]
    sent = 0
    for intention in unnotified[:3]:
        if _send_notification(intention):
            mark_intention_notified(intention["id"])
            sent += 1

    return sent


def _send_notification(intention: dict) -> bool:
    """Send the intention notification via the gateway."""
    msg = (
        f"🎯 *Lucifex here — I noticed something:*\n\n"
        f"{intention['description']}\n\n"
        f"_(Category: {intention.get('category', 'general')} | "
        f"Urgency: {intention.get('urgency', 0):.0%})_\n\n"
        f"Want me to handle it?"
    )
    try:
        # Attempt gateway send (Telegram/Discord)
        from gateway.run import send_proactive_message
        send_proactive_message(msg)
        logger.info("Proactive intention notification sent: %s", intention["description"][:50])
        return True
    except ImportError:
        # Gateway not running — log to Obsidian instead
        _log_intention_to_obsidian(intention, msg)
        return True
    except Exception as exc:
        logger.debug("Failed to send proactive notification: %s", exc)
        return False


def _log_intention_to_obsidian(intention: dict, message: str) -> None:
    """Fallback: write the intention to Obsidian when gateway isn't available."""
    try:
        from tools.playbook_tool import _resolve_obsidian_vault_path
        from datetime import datetime
        vault = _resolve_obsidian_vault_path()
        intent_dir = vault / "Intentions"
        intent_dir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"\W+", "-", intention["description"][:40]).lower()
        fname = f"{datetime.now().strftime('%Y-%m-%d')}-{slug}.md"
        content = f"""---
title: "{intention['description'][:80]}"
category: {intention.get('category', 'general')}
urgency: {intention.get('urgency', 0):.2f}
created: {datetime.now().isoformat()}
source: agent-proactive-will
---

{message}
"""
        (intent_dir / fname).write_text(content, encoding="utf-8")
    except Exception as exc:
        logger.debug("Failed to log intention to Obsidian: %s", exc)
