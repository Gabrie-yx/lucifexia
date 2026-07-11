"""agent/red_team.py — Adversarial Red Team internal validation.

Before delivering any solution, the agent can spawn an adversarial subagent
(the "red team") to attack its own proposed solution — finding edge cases,
security holes, logical flaws, and counter-arguments.

The blue agent proposes → red agent attacks → blue agent refines.
Up to 3 rounds. Converges when red team runs out of meaningful objections.

This ensures the user receives battle-tested solutions, not first drafts.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_MAX_ROUNDS = 3
_MIN_WORD_COUNT_FOR_RED_TEAM = 50  # Skip trivial responses


def should_red_team(response: str, task_type: str = "") -> bool:
    """Decide whether a response warrants red team review."""
    if len(response.split()) < _MIN_WORD_COUNT_FOR_RED_TEAM:
        return False
    high_stakes = any(kw in task_type.lower() for kw in [
        "architecture", "security", "deploy", "migration", "design", "plan",
        "refactor", "database", "api", "auth", "production",
    ])
    return high_stakes


def run_red_team(
    proposal: str,
    context: str = "",
    domain: str = "software engineering",
    max_rounds: int = _MAX_ROUNDS,
) -> dict:
    """Run the adversarial red team loop.

    Returns: {
        "final_proposal": str,   — refined proposal after red team
        "objections": list[str], — all objections raised
        "rounds": int,           — number of rounds completed
        "confidence": str,       — "high" | "medium" | "low"
    }
    """
    try:
        from agent.oneshot import run_oneshot
    except ImportError:
        logger.debug("Red team unavailable: oneshot module not found.")
        return {"final_proposal": proposal, "objections": [], "rounds": 0, "confidence": "unknown"}

    current_proposal = proposal
    all_objections = []
    rounds_completed = 0

    for round_num in range(1, max_rounds + 1):
        logger.debug("Red team round %d/%d", round_num, max_rounds)

        # ── Red Agent: Attack ────────────────────────────────────────────
        red_prompt = f"""You are a highly critical technical red team agent in {domain}.
Your job is to find REAL flaws in the following proposal.

Context: {context[:500] if context else 'none'}

Proposal:
{current_proposal}

Identify the 2-3 most serious problems: edge cases that break it, security holes,
scalability limits, incorrect assumptions, or missing error handling.
Be specific and concrete — cite exact parts of the proposal.
If the proposal is genuinely solid and you can't find meaningful flaws, respond with exactly: "NO_OBJECTIONS"
"""
        red_response = run_oneshot(red_prompt, max_tokens=400)
        if not red_response:
            break

        red_response = red_response.strip()
        if "NO_OBJECTIONS" in red_response:
            logger.debug("Red team converged at round %d — no objections.", round_num)
            rounds_completed = round_num
            break

        all_objections.append(f"Round {round_num}: {red_response}")

        # ── Blue Agent: Refine ───────────────────────────────────────────
        blue_prompt = f"""You are refining your proposal based on red team criticism.

Original proposal:
{current_proposal}

Red team objections (round {round_num}):
{red_response}

Revise the proposal to address ALL the objections above.
Keep what is good. Fix what is wrong. Be specific and complete.
"""
        refined = run_oneshot(blue_prompt, max_tokens=600)
        if refined and refined.strip():
            current_proposal = refined.strip()

        rounds_completed = round_num

    # Determine confidence based on how many rounds it took
    if rounds_completed == 0 or (rounds_completed == 1 and not all_objections):
        confidence = "high"
    elif rounds_completed <= 2:
        confidence = "medium"
    else:
        confidence = "low" if len(all_objections) >= max_rounds else "medium"

    return {
        "final_proposal": current_proposal,
        "objections": all_objections,
        "rounds": rounds_completed,
        "confidence": confidence,
    }


def red_team_wrapper(
    proposal: str,
    task_type: str = "",
    context: str = "",
) -> str:
    """Convenience wrapper: run red team if warranted, return final proposal.

    Returns the final (possibly refined) proposal as a string.
    If red team is skipped, returns the original proposal unchanged.
    """
    if not should_red_team(proposal, task_type):
        return proposal

    logger.info("Red team engaged for task_type='%s'", task_type)
    result = run_red_team(proposal, context=context)
    rounds = result.get("rounds", 0)
    objections = result.get("objections", [])
    confidence = result.get("confidence", "unknown")

    if objections:
        logger.info(
            "Red team completed: %d round(s), %d objection(s), confidence=%s",
            rounds, len(objections), confidence,
        )

    return result.get("final_proposal", proposal)
