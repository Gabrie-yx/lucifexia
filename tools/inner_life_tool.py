"""tools/inner_life_tool.py — Exposes the agent's inner state as a model tool.

Registered under the 'skills' toolset. The model can call `get_inner_state`
at any time to inspect its own mood, active intentions, curiosity queue,
pending hypotheses, and recent self-reflections.

This gives the agent genuine self-awareness: it knows what it's been
thinking about, what it wants to do, and how it has been performing.
"""
from __future__ import annotations

import json
import logging

from tools.registry import registry

logger = logging.getLogger(__name__)


def get_inner_state() -> str:
    """Return a JSON snapshot of the agent's current inner life state."""
    try:
        from agent.inner_life import get_full_state, init_db
        init_db()
        state = get_full_state()

        # Enrich mood with human-readable hint
        from agent.emotional_state import get_current_mood_summary
        state["mood_summary"] = get_current_mood_summary()

        return json.dumps(state, indent=2, ensure_ascii=False, default=str)
    except Exception as exc:
        logger.debug("get_inner_state failed: %s", exc)
        return json.dumps({"error": str(exc)})


registry.register(
    name="get_inner_state",
    toolset="skills",
    schema={
        "name": "get_inner_state",
        "description": (
            "Return a snapshot of your own inner life: current mood, active intentions "
            "(things you want to do proactively), curiosity queue (questions you haven't "
            "answered), pending hypotheses about the codebase, and recent self-reflections. "
            "Call this to introspect and understand your own state of mind."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    handler=get_inner_state,
    description="Introspect the agent's inner life state (mood, intentions, curiosities, hypotheses, reflections).",
    emoji="🧠",
)
