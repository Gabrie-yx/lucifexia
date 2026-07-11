"""agent/parallel_arbitration.py — Multi-specialist panel for Lucifex. (Feature 27)

For complex problems, spawns N specialized subagents simultaneously:
  - Security specialist (finds vulnerabilities)
  - Performance specialist (finds bottlenecks)
  - Maintainability specialist (finds long-term risks)
  - Devil's advocate (attacks the solution)

The master agent moderates the panel, identifies consensus vs. conflicts,
and synthesizes a final answer that survived all four perspectives.
"""
from __future__ import annotations

import json
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

SPECIALISTS = {
    "security": (
        "You are a ruthless security expert. Find every vulnerability, injection point, "
        "authentication flaw, privilege escalation risk, and data exposure in the proposed solution. "
        "Be specific. Reference OWASP Top 10 where applicable."
    ),
    "performance": (
        "You are a systems performance engineer. Find every bottleneck: O(n²) algorithms, "
        "missing indexes, N+1 queries, unnecessary serialization, blocking I/O, memory leaks, "
        "and scalability cliffs. Be specific about thresholds where performance degrades."
    ),
    "maintainability": (
        "You are a senior software architect focused on long-term maintainability. "
        "Find coupling problems, missing abstractions, God classes, violation of SOLID principles, "
        "missing tests, unclear naming, and technical debt that will compound over time."
    ),
    "devil": (
        "You are a devil's advocate. Your job is to find the FUNDAMENTAL flaw in the approach — "
        "not edge cases, but the core assumption that, if wrong, makes the entire solution invalid. "
        "Challenge the premise, not just the implementation."
    ),
}


def _run_specialist(
    specialist_name: str,
    persona: str,
    problem: str,
    solution: str,
    results: dict,
    lock: threading.Lock,
) -> None:
    """Run one specialist analysis in a thread."""
    try:
        from agent.oneshot import run_oneshot
        prompt = (
            f"{persona}\n\n"
            f"Problem being solved:\n{problem[:400]}\n\n"
            f"Proposed solution:\n{solution[:600]}\n\n"
            f"Provide your specialist critique in 3-5 specific, actionable bullet points. "
            f"If the solution is genuinely solid in your domain, say so explicitly."
        )
        result = run_oneshot(prompt, max_tokens=350)
        with lock:
            results[specialist_name] = result or "No critique generated."
    except Exception as exc:
        with lock:
            results[specialist_name] = f"[Specialist unavailable: {exc}]"


def _synthesize_panel(
    problem: str,
    solution: str,
    specialist_results: dict,
) -> str:
    """Synthesize specialist panel results into a final answer."""
    try:
        from agent.oneshot import run_oneshot
        panel_text = "\n\n".join(
            f"=== {name.upper()} SPECIALIST ===\n{critique}"
            for name, critique in specialist_results.items()
        )
        prompt = (
            f"You are the lead architect moderating a specialist panel review.\n\n"
            f"Original problem:\n{problem[:300]}\n\n"
            f"Proposed solution:\n{solution[:500]}\n\n"
            f"Specialist panel findings:\n{panel_text}\n\n"
            f"Synthesize the panel findings:\n"
            f"1. Points of consensus (all or most specialists agree)\n"
            f"2. Critical issues that MUST be addressed before shipping\n"
            f"3. Nice-to-haves (real but lower priority)\n"
            f"4. Final verdict: APPROVED / APPROVED WITH CONDITIONS / REJECTED\n"
            f"5. Revised solution that addresses all critical issues\n\n"
            f"Be decisive and concrete."
        )
        return run_oneshot(prompt, max_tokens=600) or "Synthesis unavailable."
    except Exception as exc:
        logger.debug("Panel synthesis failed: %s", exc)
        return f"Synthesis failed: {exc}"


def run_panel(
    problem: str,
    solution: str,
    specialists: Optional[list] = None,
    timeout: float = 45.0,
) -> dict:
    """Run the specialist panel in parallel.

    Returns:
        {
            "specialist_results": {name: critique},
            "synthesis": str,
            "verdict": "APPROVED" | "APPROVED WITH CONDITIONS" | "REJECTED",
            "specialists_used": [names],
        }
    """
    active = specialists or list(SPECIALISTS.keys())
    results: dict = {}
    lock = threading.Lock()
    threads = []

    for name in active:
        if name not in SPECIALISTS:
            continue
        t = threading.Thread(
            target=_run_specialist,
            args=(name, SPECIALISTS[name], problem, solution, results, lock),
            daemon=True,
        )
        threads.append(t)
        t.start()

    # Wait with timeout
    for t in threads:
        t.join(timeout=timeout / len(threads))

    synthesis = _synthesize_panel(problem, solution, results)

    # Extract verdict
    verdict = "APPROVED WITH CONDITIONS"
    if synthesis:
        upper = synthesis.upper()
        if "VERDICT: APPROVED\n" in upper or "VERDICT: APPROVED " in upper:
            if "WITH CONDITIONS" not in upper:
                verdict = "APPROVED"
        elif "REJECTED" in upper:
            verdict = "REJECTED"

    return {
        "specialist_results": results,
        "synthesis": synthesis,
        "verdict": verdict,
        "specialists_used": list(results.keys()),
    }


def should_use_panel(problem: str, solution: str) -> bool:
    """Decide whether a problem warrants panel review."""
    triggers = [
        "architecture", "design", "database schema", "api design",
        "security", "deploy", "production", "migration", "refactor",
        "authentication", "authorization", "payment", "encryption",
    ]
    combined = (problem + solution).lower()
    return any(t in combined for t in triggers) and len(solution.split()) > 80
