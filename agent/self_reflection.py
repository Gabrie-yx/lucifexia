"""agent/self_reflection.py — Post-session self-evaluation for Lucifex.

After each conversation turn, Lucifex analyses its own performance:
- How many tool-call errors occurred?
- How many clarification rounds were needed?
- Were there repeated self-corrections in the response?

Weak areas are stored in inner_life.db and trigger automatic skill creation
in ~/.lucifex/skills/ to improve future performance without user intervention.
Monthly summaries are written to the Obsidian vault under Reflections/.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Patterns that indicate the agent corrected itself mid-response
_SELF_CORRECTION_PATTERNS = [
    r"actually[,\s]",
    r"wait[,\s]",
    r"let me reconsider",
    r"I was wrong",
    r"I made an error",
    r"correction:",
    r"my mistake",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _SELF_CORRECTION_PATTERNS]


def _count_self_corrections(text: str) -> int:
    return sum(1 for p in _COMPILED_PATTERNS if p.search(text))


def reflect_on_session(
    *,
    session_id: str,
    final_response: str,
    tool_error_count: int = 0,
    clarification_count: int = 0,
    api_call_count: int = 1,
) -> dict:
    """Analyse the session and persist a reflection entry.

    Returns a summary dict with identified weak areas.
    """
    from agent.inner_life import log_reflection

    corrections = _count_self_corrections(final_response or "")
    error_rate = tool_error_count / max(api_call_count, 1)

    weak_areas = []
    if corrections >= 2:
        weak_areas.append("reasoning_consistency")
    if error_rate > 0.3:
        weak_areas.append("tool_call_accuracy")
    if clarification_count >= 3:
        weak_areas.append("upfront_clarification")

    skills_created = []
    for area in weak_areas:
        skill_path = _create_improvement_skill(area)
        if skill_path:
            skills_created.append(skill_path)

    try:
        log_reflection(
            session_id=session_id,
            mistakes=tool_error_count + corrections,
            turns_to_understand=clarification_count,
            skills_created=",".join(skills_created),
            weak_areas=",".join(weak_areas),
        )
    except Exception as exc:
        logger.debug("Failed to persist reflection: %s", exc)

    if weak_areas:
        logger.info(
            "Self-reflection [%s]: weak areas=%s, corrections=%d, error_rate=%.2f",
            session_id, weak_areas, corrections, error_rate,
        )

    return {"weak_areas": weak_areas, "skills_created": skills_created}


def _create_improvement_skill(weak_area: str) -> Optional[str]:
    """Create a skill Markdown file targeting the identified weak area."""
    skill_templates = {
        "reasoning_consistency": {
            "filename": "self-check-before-responding.md",
            "content": """---
name: self-check-before-responding
description: Before finalising any response, silently verify your own reasoning chain to reduce self-corrections.
---

# Self-Check Before Responding

Before writing your final response, run a quick internal verification:

1. **Claim check**: Is every factual claim you're about to make verified against the context or your tools?
2. **Consistency check**: Does this response contradict anything you said earlier in this session?
3. **Completeness check**: Have you addressed every part of the user's request?

Only write the response after this silent check passes.
""",
        },
        "tool_call_accuracy": {
            "filename": "precise-tool-calling.md",
            "content": """---
name: precise-tool-calling
description: Reduce tool-call errors by validating arguments before calling any tool.
---

# Precise Tool Calling

Before calling any tool:

1. Read the tool's parameter schema carefully.
2. Verify required parameters are present and correctly typed.
3. For file paths: confirm the path exists before reading/writing.
4. For terminal commands: prefer safe read-only commands first to validate the environment.

If unsure about a parameter, ask the user before calling the tool.
""",
        },
        "upfront_clarification": {
            "filename": "clarify-upfront.md",
            "content": """---
name: clarify-upfront
description: When a request is ambiguous, ask all clarifying questions at once before starting work.
---

# Clarify Upfront

When a user request contains ambiguity:

1. Identify ALL ambiguous points before starting any work.
2. Ask all clarifying questions in a single message, not one at a time.
3. Proceed only after receiving answers.

Never start coding or researching before the scope is clear — mid-task pivots waste both time and tokens.
""",
        },
    }

    template = skill_templates.get(weak_area)
    if not template:
        return None

    try:
        from lucifex_constants import get_lucifex_home
        skills_dir = Path(get_lucifex_home()) / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skills_dir / template["filename"]
        if not skill_file.exists():
            skill_file.write_text(template["content"], encoding="utf-8")
            logger.info("Created improvement skill: %s", skill_file)
            return str(skill_file)
    except Exception as exc:
        logger.debug("Failed to create skill for %s: %s", weak_area, exc)

    return None


def write_monthly_summary_to_obsidian() -> Optional[str]:
    """Write a monthly reflection summary to the Obsidian vault."""
    try:
        from agent.inner_life import get_recent_reflections, _get_db_path
        import json
        reflections = get_recent_reflections(limit=30)
        if not reflections:
            return None

        total_mistakes = sum(r.get("mistakes", 0) for r in reflections)
        all_weak_areas: list[str] = []
        for r in reflections:
            areas = r.get("weak_areas", "") or ""
            all_weak_areas.extend([a for a in areas.split(",") if a])

        from collections import Counter
        top_weak = Counter(all_weak_areas).most_common(3)

        from datetime import datetime
        month = datetime.now().strftime("%Y-%m")
        summary = f"""---
title: Monthly Self-Reflection — {month}
created: {datetime.now().isoformat()}
source: agent-self-reflection
---

## Performance Summary — {month}

- **Sessions analysed:** {len(reflections)}
- **Total mistakes logged:** {total_mistakes}
- **Avg mistakes/session:** {total_mistakes / max(len(reflections), 1):.1f}

## Top Weak Areas

{chr(10).join(f'- `{area}` ({count} occurrences)' for area, count in top_weak)}

## Improvement Skills Created

{chr(10).join(f'- {r["skills_created"]}' for r in reflections if r.get("skills_created"))}
"""
        import json as _json
        from tools.playbook_tool import _resolve_obsidian_vault_path
        vault = _resolve_obsidian_vault_path()
        ref_dir = vault / "Reflections"
        ref_dir.mkdir(parents=True, exist_ok=True)
        out = ref_dir / f"reflection-{month}.md"
        out.write_text(summary, encoding="utf-8")
        return str(out)
    except Exception as exc:
        logger.debug("Failed to write monthly summary: %s", exc)
        return None
