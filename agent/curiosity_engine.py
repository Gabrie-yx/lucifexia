"""agent/curiosity_engine.py — Autonomous curiosity loop for Lucifex.

Detects unanswered questions and knowledge gaps in the agent's responses,
queues them in inner_life.db, and researches them autonomously during idle
periods (run via cron). Findings are written to the Obsidian vault.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Patterns that indicate uncertainty or an unanswered question
_UNCERTAINTY_PATTERNS = [
    r"I('m| am) not (sure|certain)",
    r"I (don't|do not) know",
    r"I (would|'d) need to (research|investigate|check|look into)",
    r"I('m| am) unsure",
    r"it's (unclear|uncertain) (to me )?whether",
    r"I lack (the|enough) (context|information|data)",
    r"would need more (research|information)",
    r"not entirely (sure|certain)",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _UNCERTAINTY_PATTERNS]


def _extract_unanswered_questions(text: str) -> list[str]:
    """Return sentences from text that express uncertainty."""
    sentences = re.split(r"(?<=[.!?])\s+", text or "")
    gaps = []
    for sentence in sentences:
        if any(p.search(sentence) for p in _COMPILED):
            cleaned = sentence.strip()
            if len(cleaned) > 20:
                gaps.append(cleaned)
    return gaps


def log_unanswered(
    response_text: str,
    context: str = "",
    session_id: str = "",
) -> int:
    """Detect and log unanswered questions from the agent's response.

    Returns the number of new curiosity items added.
    """
    from agent.inner_life import add_curiosity

    gaps = _extract_unanswered_questions(response_text)
    added = 0
    for gap in gaps:
        try:
            add_curiosity(question=gap, context=context[:500], session_id=session_id)
            added += 1
            logger.debug("Curiosity queued: %s", gap[:80])
        except Exception as exc:
            logger.debug("Failed to queue curiosity: %s", exc)
    return added


def process_curiosity_queue(max_items: int = 3) -> list[dict]:
    """Research pending curiosities and write findings to Obsidian.

    Called by the cron job during idle periods. Returns processed items.
    """
    from agent.inner_life import get_pending_curiosities, resolve_curiosity

    pending = get_pending_curiosities(limit=max_items)
    if not pending:
        logger.debug("Curiosity queue empty — nothing to process.")
        return []

    processed = []
    for item in pending:
        result = _research_question(item["question"], item.get("context", ""))
        if result:
            _write_discovery_to_obsidian(item["question"], result)
            try:
                resolve_curiosity(item["id"])
            except Exception as exc:
                logger.debug("Failed to mark curiosity resolved: %s", exc)
            processed.append({"question": item["question"], "finding": result})
            logger.info("Curiosity resolved: %s", item["question"][:60])

    return processed


def _research_question(question: str, context: str) -> Optional[str]:
    """Attempt to research a question using available tools.

    Uses a lightweight model call to synthesise an answer from web search
    or internal knowledge. Returns the answer text or None.
    """
    try:
        # Use the web_search tool if available, otherwise fall back to
        # the agent's internal knowledge via a one-shot prompt.
        from agent.oneshot import run_oneshot
        prompt = (
            f"Research this question concisely and factually. "
            f"Context: {context[:300] if context else 'none'}.\n\n"
            f"Question: {question}\n\n"
            f"Provide a 2–4 sentence answer based on your knowledge or web research."
        )
        result = run_oneshot(prompt, max_tokens=300)
        return result.strip() if result else None
    except Exception as exc:
        logger.debug("Research failed for question '%s': %s", question[:50], exc)
        return None


def _write_discovery_to_obsidian(question: str, finding: str) -> None:
    """Write a curiosity finding to the Obsidian vault Discoveries/ folder."""
    try:
        from tools.playbook_tool import _resolve_obsidian_vault_path
        from datetime import datetime
        import re as _re

        vault = _resolve_obsidian_vault_path()
        disc_dir = vault / "Discoveries"
        disc_dir.mkdir(parents=True, exist_ok=True)

        slug = _re.sub(r"[^\w\s-]", "", question[:50]).strip().lower()
        slug = _re.sub(r"\s+", "-", slug)
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date_str}-curiosity-{slug[:40]}.md"

        content = f"""---
title: "{question[:80]}"
category: curiosity
impact: low
created: {datetime.now().isoformat()}
source: agent-curiosity-engine
tags:
  - curiosity
  - autonomous-research
---

## Question

{question}

## Finding

{finding}
"""
        (disc_dir / filename).write_text(content, encoding="utf-8")
        logger.info("Curiosity discovery written: %s", filename)
    except Exception as exc:
        logger.debug("Failed to write curiosity discovery: %s", exc)
