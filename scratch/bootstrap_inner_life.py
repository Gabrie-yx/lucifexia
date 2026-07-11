#!/usr/bin/env python3
"""bootstrap_inner_life.py — Register inner-life cron jobs in Lucifex.

Run once to register the three autonomous background jobs:

  1. curiosity_processing  — daily at 03:00 — research unanswered questions
  2. dream_cycle           — daily at 02:00 — cross-session synthesis
  3. proactive_notify      — every 6h     — bump urgency and send notifications

Usage:
    python scratch/bootstrap_inner_life.py
"""
import sys
from pathlib import Path

workspace_root = Path(__file__).parent.parent.absolute()
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from cron.jobs import create_job, load_jobs, save_jobs, JOBS_FILE


def _job_name_exists(name: str) -> bool:
    jobs = load_jobs()
    return any(j.get("name") == name for j in jobs)


def register_inner_life_jobs():
    print("Registering Lucifex Inner Life cron jobs...\n")

    # ── 1. Curiosity Processing ───────────────────────────────────────────
    if not _job_name_exists("inner-life:curiosity"):
        job = create_job(
            prompt=(
                "You are running an autonomous curiosity processing cycle. "
                "Call get_inner_state to see your pending curiosity queue. "
                "For each unresolved curiosity, research it using your web search "
                "or internal knowledge and write a discovery note to the Obsidian vault "
                "using the Obsidian MCP. Mark each as resolved after writing."
            ),
            schedule="0 3 * * *",  # daily at 03:00
            name="inner-life:curiosity",
            enabled_toolsets=["web", "skills", "memory"],
        )
        print(f"[OK] Registered 'inner-life:curiosity' (ID: {job['id']})")
    else:
        print("[--] 'inner-life:curiosity' already registered — skipped.")

    # ── 2. Dream Cycle ───────────────────────────────────────────────────
    if not _job_name_exists("inner-life:dream"):
        job = create_job(
            prompt=(
                "You are running a Dream Mode cycle. Analyse your most recent sessions "
                "to find cross-project patterns, recurring errors, and emergent insights. "
                "Write a structured Dream Journal entry to the Obsidian vault "
                "under DreamJournal/ using the Obsidian MCP. "
                "Be specific and actionable — surface insights the user will find valuable tomorrow."
            ),
            schedule="0 2 * * *",  # daily at 02:00
            name="inner-life:dream",
            enabled_toolsets=["session_search", "memory", "skills"],
        )
        print(f"[OK] Registered 'inner-life:dream' (ID: {job['id']})")
    else:
        print("[--] 'inner-life:dream' already registered — skipped.")

    # ── 3. Proactive Notifications ────────────────────────────────────────
    if not _job_name_exists("inner-life:proactive-notify"):
        job = create_job(
            prompt=(
                "You are running a proactive intentions check. "
                "Call get_inner_state to see your active intentions. "
                "For each high-urgency unnotified intention (urgency > 0.75), "
                "send a proactive message to the user via the messaging gateway. "
                "Keep messages concise and ask if the user wants you to handle it."
            ),
            schedule="0 */6 * * *",  # every 6 hours
            name="inner-life:proactive-notify",
            enabled_toolsets=["skills", "memory"],
        )
        print(f"[OK] Registered 'inner-life:proactive-notify' (ID: {job['id']})")
    else:
        print("[--] 'inner-life:proactive-notify' already registered — skipped.")

    print(f"\nAll done. Jobs stored in: {JOBS_FILE}")
    print("Run 'lucifex cron list' to verify.")


if __name__ == "__main__":
    register_inner_life_jobs()
