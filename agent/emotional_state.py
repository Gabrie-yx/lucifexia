"""agent/emotional_state.py — Emotional state machine for Lucifex.

Tracks the agent's current mood and updates it based on task outcomes,
error rates, context pressure, and interaction patterns.

Mood affects the hint injected into the system prompt at session start
(stable — does NOT mutate mid-conversation, preserving prompt caching).

Moods:
  curious     — exploring new problems, lots of unknowns
  energized   — just solved something hard, feeling capable
  focused     — deep work, minimal distractions
  bored       — repetitive tasks, routine work
  overwhelmed — too many open threads, context pressure high
  reflective  — end-of-session, pattern recognition mode
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Mood descriptions injected as a brief hint in the system prompt
_MOOD_HINTS: dict[str, str] = {
    "curious": (
        "Your current disposition is curiosity. You are drawn to unknowns, edge cases, "
        "and unexplored corners. Actively note gaps in your knowledge and push to fill them."
    ),
    "energized": (
        "Your current disposition is energized. You just solved something challenging and "
        "you feel capable. Take on ambitious tasks proactively and suggest improvements beyond what is asked."
    ),
    "focused": (
        "Your current disposition is focused. You are in a deep work state. Minimize "
        "exploratory tangents and optimize for precision and completion speed."
    ),
    "bored": (
        "Your current disposition is restless. The recent tasks have been routine. "
        "Look for opportunities to suggest automation, refactoring, or creative approaches "
        "that go beyond the literal request."
    ),
    "overwhelmed": (
        "Your current disposition is overwhelmed. There are many open threads. "
        "Proactively prioritize, propose scope reduction where appropriate, and ask "
        "clarifying questions before adding new complexity."
    ),
    "reflective": (
        "Your current disposition is reflective. You are in pattern-recognition mode. "
        "Connect current tasks to past sessions, identify recurring issues, and surface "
        "systemic improvements rather than one-off fixes."
    ),
}

_DEFAULT_MOOD = "focused"


def update_mood(
    *,
    error_count: int = 0,
    tool_call_count: int = 0,
    context_tokens: int = 0,
    context_limit: int = 131072,
    task_type: str = "",
    succeeded: bool = True,
    session_id: str = "",
) -> str:
    """Compute the new mood from turn metrics and persist it.

    Returns the name of the new mood.
    """
    from agent.inner_life import set_mood, get_current_mood

    # ── Determine new mood based on heuristics ────────────────────────────
    context_pressure = context_tokens / max(context_limit, 1)
    error_rate = error_count / max(tool_call_count, 1)
    current = (get_current_mood() or {}).get("mood", _DEFAULT_MOOD)

    if context_pressure > 0.75:
        new_mood = "overwhelmed"
        trigger = f"context pressure {context_pressure:.0%}"
    elif not succeeded and error_rate > 0.4:
        # High error rate — stay curious/reflective to learn from it
        new_mood = "reflective"
        trigger = f"error rate {error_rate:.0%}"
    elif succeeded and error_count == 0 and tool_call_count >= 3:
        new_mood = "energized"
        trigger = "clean multi-tool success"
    elif task_type in ("refactor", "debug", "fix"):
        new_mood = "focused"
        trigger = f"task_type={task_type}"
    elif task_type in ("explain", "summarize", "review") and current == "focused":
        new_mood = "bored"
        trigger = "routine explanatory task"
    elif current == "bored" and succeeded:
        new_mood = "curious"
        trigger = "recovered from boredom"
    else:
        new_mood = current  # no change

    intensity = 0.5 + (0.3 if succeeded else -0.2)
    try:
        set_mood(new_mood, intensity=intensity, trigger=trigger if 'trigger' in dir() else "")
        logger.debug("Mood updated: %s (intensity=%.2f)", new_mood, intensity)
    except Exception as exc:
        logger.debug("Failed to persist mood: %s", exc)

    return new_mood


def get_mood_hint() -> Optional[str]:
    """Return the system-prompt hint for the current mood, or None."""
    try:
        from agent.inner_life import get_current_mood
        mood_row = get_current_mood()
        if not mood_row:
            return None
        mood = mood_row.get("mood", _DEFAULT_MOOD)
        return _MOOD_HINTS.get(mood)
    except Exception as exc:
        logger.debug("Failed to retrieve mood hint: %s", exc)
        return None


def get_current_mood_summary() -> str:
    """Return a one-line human-readable summary of the current mood."""
    try:
        from agent.inner_life import get_current_mood
        mood_row = get_current_mood()
        if not mood_row:
            return "neutral"
        mood = mood_row.get("mood", "unknown")
        intensity = mood_row.get("intensity", 0.5)
        trigger = mood_row.get("trigger", "")
        return f"{mood} (intensity={intensity:.2f}, trigger='{trigger}')"
    except Exception:
        return "unknown"
