"""agent/predictor.py — Predictive Pre-execution for Lucifex.

The agent analyses the current conversation context and pre-executes
the most likely next requests in background threads. When the user
actually asks, the answer may already be ready.

Strategy:
1. At end of each turn, extract 2-3 likely follow-up intents
2. Pre-run lightweight versions in background (no side effects)
3. Cache results keyed by context hash
4. On next turn, check cache before calling API

Only pure read/analysis tasks are pre-executed — never write ops.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

_cache: dict[str, dict] = {}
_cache_lock = threading.RLock()
_MAX_CACHE_SIZE = 20
_CACHE_TTL_SECONDS = 600  # 10 minutes


# ── Cache Management ──────────────────────────────────────────────────────────

def _cache_key(context: str, intent: str) -> str:
    payload = f"{context[:500]}|{intent}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _store(key: str, result: Any, intent: str) -> None:
    with _cache_lock:
        if len(_cache) >= _MAX_CACHE_SIZE:
            # Evict oldest
            oldest = min(_cache, key=lambda k: _cache[k].get("timestamp", 0))
            del _cache[oldest]
        _cache[key] = {
            "result": result,
            "intent": intent,
            "timestamp": time.time(),
        }
    logger.debug("Prediction cached: %s → %s", intent[:40], key)


def lookup(context: str, current_message: str) -> Optional[dict]:
    """Check if a pre-computed result exists for this context+message."""
    key = _cache_key(context, current_message)
    with _cache_lock:
        entry = _cache.get(key)
    if entry:
        age = time.time() - entry.get("timestamp", 0)
        if age < _CACHE_TTL_SECONDS:
            logger.debug("Prediction cache HIT for: %s", current_message[:50])
            return entry
        else:
            with _cache_lock:
                _cache.pop(key, None)
    return None


def _is_safe_to_preexecute(intent: str) -> bool:
    """Only pre-execute read/analyse intents — never destructive ones."""
    safe_keywords = [
        "list", "show", "get", "read", "find", "search", "check", "analyse",
        "analyze", "explain", "describe", "what", "how", "why", "count",
        "status", "summary", "review", "inspect",
    ]
    unsafe_keywords = [
        "delete", "drop", "remove", "write", "create", "deploy", "send",
        "execute", "run", "modify", "update", "install", "push",
    ]
    intent_lower = intent.lower()
    has_safe = any(kw in intent_lower for kw in safe_keywords)
    has_unsafe = any(kw in intent_lower for kw in unsafe_keywords)
    return has_safe and not has_unsafe


# ── Intent Extraction ─────────────────────────────────────────────────────────

def _extract_likely_followups(
    last_user_message: str,
    agent_response: str,
    session_context: str = "",
) -> list[str]:
    """Extract likely follow-up intents from the current conversation turn."""
    try:
        from agent.oneshot import run_oneshot
        prompt = (
            f"Based on this conversation exchange, predict the 2 most likely follow-up questions "
            f"or requests the user will make next. Be specific and concrete.\n\n"
            f"User asked: {last_user_message[:300]}\n"
            f"Agent responded: {agent_response[:400]}\n\n"
            f"Return ONLY a JSON array of 2 short intent strings:\n"
            f'["intent 1", "intent 2"]'
        )
        result = run_oneshot(prompt, max_tokens=150)
        if not result:
            return []
        import re
        match = re.search(r"\[.*?\]", result, re.DOTALL)
        if match:
            return json.loads(match.group())[:2]
    except Exception as exc:
        logger.debug("Intent extraction failed: %s", exc)
    return []


# ── Pre-execution Runners ─────────────────────────────────────────────────────

_PREEXECUTION_HANDLERS: dict[str, Callable] = {}


def register_preexecution_handler(intent_pattern: str, handler: Callable) -> None:
    """Register a function to pre-execute when an intent matches the pattern."""
    _PREEXECUTION_HANDLERS[intent_pattern] = handler


def _find_handler(intent: str) -> Optional[tuple[str, Callable]]:
    """Find a matching handler for an intent."""
    intent_lower = intent.lower()
    for pattern, handler in _PREEXECUTION_HANDLERS.items():
        if pattern.lower() in intent_lower:
            return pattern, handler
    return None


def _preexecute_intent(context: str, intent: str) -> None:
    """Run pre-execution for a single intent in background."""
    if not _is_safe_to_preexecute(intent):
        return

    key = _cache_key(context, intent)
    with _cache_lock:
        if key in _cache:
            return  # Already cached

    match = _find_handler(intent)
    if match:
        pattern, handler = match
        try:
            result = handler(intent)
            _store(key, result, intent)
        except Exception as exc:
            logger.debug("Pre-execution handler failed (%s): %s", pattern, exc)
        return

    # Generic: run a lightweight oneshot for analysis intents
    if any(kw in intent.lower() for kw in ["analyse", "analyze", "explain", "summarise", "summarize"]):
        try:
            from agent.oneshot import run_oneshot
            result = run_oneshot(f"{intent}\nContext: {context[:300]}", max_tokens=400)
            if result:
                _store(key, result, intent)
        except Exception as exc:
            logger.debug("Generic pre-execution failed: %s", exc)


def preexecute_followups(
    last_user_message: str,
    agent_response: str,
    session_context: str = "",
) -> None:
    """Extract likely follow-ups and pre-execute them in background.

    Call this at the end of each turn. Fire-and-forget — does not block.
    """
    def _worker():
        intents = _extract_likely_followups(last_user_message, agent_response, session_context)
        if not intents:
            return
        logger.debug("Prediction: pre-executing %d intent(s): %s", len(intents), intents)
        for intent in intents:
            _preexecute_intent(session_context + last_user_message, intent)

    t = threading.Thread(target=_worker, daemon=True, name="predictor-worker")
    t.start()


# ── Built-in Handlers ─────────────────────────────────────────────────────────

def _handle_file_list_intent(intent: str) -> Optional[str]:
    """Pre-fetch file listings for likely file-related follow-ups."""
    import re
    path_match = re.search(r"(?:in|from|under|at)\s+([\w/.\\~-]+)", intent)
    if path_match:
        path = Path(path_match.group(1)).expanduser()
        if path.exists() and path.is_dir():
            files = sorted(path.iterdir())
            return json.dumps([str(f.name) for f in files[:50]])
    return None


def _handle_git_status_intent(intent: str) -> Optional[str]:
    import subprocess
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout if result.returncode == 0 else None
    except Exception:
        return None


# Register built-in handlers
register_preexecution_handler("list files", _handle_file_list_intent)
register_preexecution_handler("git status", _handle_git_status_intent)


# ── Cache Stats ───────────────────────────────────────────────────────────────

def get_cache_stats() -> dict:
    with _cache_lock:
        size = len(_cache)
        intents = [v.get("intent", "?") for v in _cache.values()]
    return {"cached_predictions": size, "intents": intents}
