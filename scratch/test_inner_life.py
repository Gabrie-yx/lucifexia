#!/usr/bin/env python3
"""scratch/test_inner_life.py — Validate all inner-life modules in isolation.

Runs each of the 6 autonomy subsystems against the real inner_life.db
(uses a tmp DB to avoid polluting the real one) and verifies that:
  - The DB schema initialises cleanly
  - Each module can read and write without errors
  - The turn_finalizer hooks don't raise
  - The prompt_builder mood hint works

Usage:
    python scratch/test_inner_life.py
"""
import os
import sys
import tempfile
from pathlib import Path

# Fix Windows console encoding for UTF-8 output
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── Bootstrap path ───────────────────────────────────────────────────────────
workspace = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(workspace))

# Redirect inner_life.db to a temp dir so we don't touch real data
_tmp = tempfile.mkdtemp(prefix="lucifex_inner_life_test_")
os.environ.setdefault("LUCIFEX_HOME_OVERRIDE_TEST", _tmp)

# Monkey-patch get_lucifex_home before importing anything
import lucifex_constants
_original_get_lucifex_home = lucifex_constants.get_lucifex_home
lucifex_constants.get_lucifex_home = lambda: Path(_tmp)

print(f"Using temp DB at: {_tmp}\n")

PASS = "  [PASS]"
FAIL = "  [FAIL]"


def section(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


# ── Test 1: inner_life.py — DB init and CRUD ─────────────────────────────────
section("1. inner_life.py — DB init & CRUD")

try:
    from agent.inner_life import (
        init_db, add_curiosity, get_pending_curiosities, resolve_curiosity,
        add_intention, get_pending_intentions, bump_intention_urgency,
        set_mood, get_current_mood,
        add_hypothesis, get_pending_hypotheses, update_hypothesis,
        log_reflection, get_recent_reflections,
        get_full_state,
    )

    init_db()
    print(f"{PASS} init_db() — schema created")

    cid = add_curiosity("What is the best caching strategy for SQLite?", "test context", "sess-001")
    assert cid > 0
    print(f"{PASS} add_curiosity() → id={cid}")

    pending = get_pending_curiosities()
    assert len(pending) == 1 and pending[0]["id"] == cid
    print(f"{PASS} get_pending_curiosities() → {len(pending)} item(s)")

    resolve_curiosity(cid)
    assert len(get_pending_curiosities()) == 0
    print(f"{PASS} resolve_curiosity()")

    iid = add_intention("Add tests for inner_life.py", "code_quality", urgency=0.8)
    assert iid > 0
    bump_intention_urgency(iid, delta=0.1)
    intents = get_pending_intentions(min_urgency=0.8)
    assert len(intents) >= 1
    print(f"{PASS} add_intention() + bump_urgency() + get_pending_intentions()")

    set_mood("curious", intensity=0.9, trigger="test")
    mood = get_current_mood()
    assert mood and mood["mood"] == "curious"
    print(f"{PASS} set_mood() + get_current_mood() → mood={mood['mood']}")

    hid = add_hypothesis("Missing index on session_id column", "lucifex_state.py", "get_session")
    update_hypothesis(hid, status="confirmed", evidence="Grep found no CREATE INDEX")
    hyps = get_pending_hypotheses()
    print(f"{PASS} add_hypothesis() + update_hypothesis()")

    rid = log_reflection("sess-001", mistakes=2, turns_to_understand=3, weak_areas="tool_call_accuracy")
    refs = get_recent_reflections()
    assert len(refs) >= 1
    print(f"{PASS} log_reflection() + get_recent_reflections()")

    state = get_full_state()
    assert "mood" in state and "pending_curiosities" in state
    print(f"{PASS} get_full_state() → keys={list(state.keys())}")

except Exception as e:
    print(f"{FAIL} inner_life — EXCEPTION: {e}")
    import traceback; traceback.print_exc()


# ── Test 2: emotional_state.py ────────────────────────────────────────────────
section("2. emotional_state.py")

try:
    from agent.emotional_state import update_mood, get_mood_hint, get_current_mood_summary

    new_mood = update_mood(
        error_count=0, tool_call_count=4, context_tokens=10000,
        succeeded=True, session_id="sess-001"
    )
    print(f"{PASS} update_mood() → {new_mood}")

    hint = get_mood_hint()
    print(f"{PASS} get_mood_hint() → {'<text>' if hint else '<None>'}")

    summary = get_current_mood_summary()
    print(f"{PASS} get_current_mood_summary() → {summary}")

except Exception as e:
    print(f"{FAIL} emotional_state — EXCEPTION: {e}")
    import traceback; traceback.print_exc()


# ── Test 3: curiosity_engine.py ───────────────────────────────────────────────
section("3. curiosity_engine.py")

try:
    from agent.curiosity_engine import _extract_unanswered_questions, log_unanswered

    text = "I'm not sure why this fails. I would need to research the SQLite locking model further."
    gaps = _extract_unanswered_questions(text)
    assert len(gaps) >= 1
    print(f"{PASS} _extract_unanswered_questions() → {len(gaps)} gap(s) found")

    count = log_unanswered(text, context="testing", session_id="sess-001")
    assert count >= 1
    print(f"{PASS} log_unanswered() → {count} item(s) queued")

except Exception as e:
    print(f"{FAIL} curiosity_engine — EXCEPTION: {e}")
    import traceback; traceback.print_exc()


# ── Test 4: self_reflection.py ────────────────────────────────────────────────
section("4. self_reflection.py")

try:
    from agent.self_reflection import _count_self_corrections, reflect_on_session

    text = "Actually, I was wrong. Wait, let me reconsider this approach."
    corrections = _count_self_corrections(text)
    assert corrections >= 2
    print(f"{PASS} _count_self_corrections() → {corrections} correction(s)")

    result = reflect_on_session(
        session_id="sess-test",
        final_response=text,
        tool_error_count=3,
        clarification_count=4,
        api_call_count=5,
    )
    print(f"{PASS} reflect_on_session() → weak_areas={result['weak_areas']}")

except Exception as e:
    print(f"{FAIL} self_reflection — EXCEPTION: {e}")
    import traceback; traceback.print_exc()


# ── Test 5: hypothesis_engine.py ─────────────────────────────────────────────
section("5. hypothesis_engine.py")

try:
    from agent.hypothesis_engine import _pattern_scan

    sample_code = '''
import sqlite3

def get_user(user_id):
    conn = sqlite3.connect("db.sqlite")
    rows = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return rows.fetchall()

for u in get_all_users():
    data = get_user(u["id"])  # N+1 query
    process(data)

try:
    do_something()
except:
    pass  # bare except
'''
    hyps = _pattern_scan("models.py", sample_code)
    assert len(hyps) >= 1
    print(f"{PASS} _pattern_scan() → {len(hyps)} hypothesis(es) generated:")
    for h in hyps:
        print(f"      → {h['hypothesis'][:80]}")

except Exception as e:
    print(f"{FAIL} hypothesis_engine — EXCEPTION: {e}")
    import traceback; traceback.print_exc()


# ── Test 6: proactive_will.py ─────────────────────────────────────────────────
section("6. proactive_will.py")

try:
    from agent.proactive_will import _check_missing_tests, _check_hardcoded_secrets

    root = workspace
    missing_tests = _check_missing_tests(root)
    print(f"{PASS} _check_missing_tests() → {len(missing_tests)} intention(s)")

    secrets = _check_hardcoded_secrets(root)
    print(f"{PASS} _check_hardcoded_secrets() → {len(secrets)} warning(s)")

except Exception as e:
    print(f"{FAIL} proactive_will — EXCEPTION: {e}")
    import traceback; traceback.print_exc()


# ── Summary ───────────────────────────────────────────────────────────────────
section("DONE")
print(f"Temp DB: {_tmp}")
print("All subsystems exercised. Review any [FAIL] lines above.\n")
