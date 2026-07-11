"""scratch/test_agi_features.py — Validate Phase 2 AGI + OS feature modules."""
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ok = []
fail = []


def test(name, fn):
    try:
        fn()
        ok.append(name)
        print(f"  [PASS] {name}")
    except Exception as e:
        fail.append(name)
        print(f"  [FAIL] {name}: {e}")
        import traceback; traceback.print_exc()


# ── World Model ────────────────────────────────────────────────────────────────
def t_world_model():
    from agent.world_model import init_world_model, add_node, add_edge, search_nodes, get_impact_chain, export_to_mermaid
    init_world_model()
    n1 = add_node("Lucifex v2", "project")
    n2 = add_node("Gabriel", "person")
    n3 = add_node("September 2026", "deadline")
    add_edge(n2, n1, "owned_by")
    add_edge(n1, n3, "precedes")
    chain = get_impact_chain(n1)
    assert "impacts" in chain, "impact chain missing"
    mermaid = export_to_mermaid()
    assert "graph LR" in mermaid, "mermaid output missing"


test("world_model", t_world_model)


# ── Long Horizon ───────────────────────────────────────────────────────────────
def t_long_horizon():
    from agent.long_horizon import (
        init_db, add_goal, add_milestone, log_progress,
        project_completion, get_active_goals,
    )
    init_db()
    gid = add_goal("Launch Lucifex v2", "Full AGI features release", "2026-09-01")
    mid = add_milestone(gid, "Implement all 17 features")
    log_progress(gid, 0.15, note="Phase 1 done")
    log_progress(gid, 0.10, note="Phase 2 done")
    proj = project_completion(gid)
    assert "progress" in proj, "projection missing progress key"
    goals = get_active_goals()
    assert len(goals) > 0, "no active goals"


test("long_horizon", t_long_horizon)


# ── Isomorphism Engine ─────────────────────────────────────────────────────────
def t_isomorphism():
    from agent.isomorphism_engine import init_db, find_similar_patterns
    init_db()
    patterns = find_similar_patterns("rate limit API requests quota exceeded")
    assert len(patterns) > 0, "no patterns found"
    assert patterns[0].get("name"), "pattern has no name"


test("isomorphism_engine", t_isomorphism)


# ── Theory of Mind ─────────────────────────────────────────────────────────────
def t_theory_of_mind():
    from agent.theory_of_mind import (
        init_db, update_from_message, proactive_misconception_warning,
    )
    init_db()
    signals = update_from_message(
        "I use SELECT * from all tables and compare floats with ==",
        session_id="test",
    )
    assert "misconceptions" in signals, "signals missing misconceptions"
    warning = proactive_misconception_warning("if value == 3.14:")
    assert warning is not None, "no warning returned for float == pattern"


test("theory_of_mind", t_theory_of_mind)


# ── Red Team ───────────────────────────────────────────────────────────────────
def t_red_team():
    from agent.red_team import should_red_team
    # Build a response longer than the 50-word threshold
    long_response = " ".join(["word"] * 60)
    assert should_red_team(long_response, "architecture"), "should red-team architecture task"
    assert not should_red_team("Yes", "chat"), "should not red-team trivial response"


test("red_team", t_red_team)


# ── Cascade Predictor ──────────────────────────────────────────────────────────
def t_cascade():
    from agent.cascade_predictor import (
        _find_n_plus_one_risks, _find_missing_indexes, _cyclomatic_complexity_estimate,
    )
    code_n1 = "for u in users:\n    result = db.execute('SELECT * FROM orders WHERE user_id = ?', u.id)"
    risks = _find_n_plus_one_risks(code_n1)
    assert len(risks) > 0, "N+1 not detected"

    code_sql = "WHERE email = ? AND status = ?"
    idx = _find_missing_indexes(code_sql)
    assert len(idx) > 0, "missing index not detected"

    code_complex = "if a:\n  if b:\n    for c in d:\n      if e or f:\n        pass"
    complexity = _cyclomatic_complexity_estimate(code_complex)
    assert complexity > 3, f"complexity underestimated: {complexity}"


test("cascade_predictor", t_cascade)


# ── Simulator ──────────────────────────────────────────────────────────────────
def t_simulator():
    from agent.simulator import is_high_risk, _classify_risk_level, _heuristic_simulation
    assert is_high_risk("DROP TABLE users"), "DROP TABLE should be high risk"
    assert not is_high_risk("ls -la"), "ls should not be high risk"
    assert _classify_risk_level("DROP DATABASE prod") == "critical"
    sim = _heuristic_simulation("deploy to production", "high")
    assert "outcomes" in sim, "simulation missing outcomes"
    assert len(sim["outcomes"]) == 3, f"expected 3 outcomes, got {len(sim['outcomes'])}"


test("simulator", t_simulator)


# ── Skill Hunter ───────────────────────────────────────────────────────────────
def t_skill_hunter():
    from agent.skill_hunter import detect_gaps, init_db
    init_db()
    text = "I can't access the Figma API from here. I don't have a tool for that integration."
    gaps = detect_gaps(text)
    assert len(gaps) > 0, "no gaps detected"


test("skill_hunter", t_skill_hunter)


# ── Predictor ──────────────────────────────────────────────────────────────────
def t_predictor():
    from agent.predictor import _is_safe_to_preexecute, _cache_key
    assert _is_safe_to_preexecute("list all files in the project")
    assert not _is_safe_to_preexecute("delete all production logs")
    key = _cache_key("ctx", "show git status")
    assert len(key) == 16, f"unexpected key length: {len(key)}"


test("predictor", t_predictor)


# ── Event Reactor ──────────────────────────────────────────────────────────────
def t_event_reactor():
    from agent.event_reactor import register_trigger, list_triggers, remove_trigger
    tid = register_trigger(
        event_type="battery_low",
        condition={"threshold": 15},
        action_type="log",
        action_payload="Battery critical — save work now",
        trigger_id="test-battery",
    )
    assert tid == "test-battery"
    triggers = list_triggers()
    assert any(t["id"] == "test-battery" for t in triggers)
    removed = remove_trigger("test-battery")
    assert removed


test("event_reactor", t_event_reactor)


# ── Clipboard Tool (structure) ─────────────────────────────────────────────────
def t_clipboard():
    from tools.clipboard_tool import _classify
    ctype, summary = _classify('{"name": "test", "value": 42}')
    assert ctype == "json", f"expected json, got {ctype}"
    ctype2, _ = _classify("https://github.com/user/repo")
    assert ctype2 == "url"
    ctype3, _ = _classify("def hello():\n    return 42")
    assert ctype3 == "python"


test("clipboard_tool", t_clipboard)


# ── Window Tool (structure) ────────────────────────────────────────────────────
def t_window_tool():
    from tools.window_tool import _BUILTIN_LAYOUTS
    assert "coding" in _BUILTIN_LAYOUTS
    assert "call" in _BUILTIN_LAYOUTS
    assert "focus" in _BUILTIN_LAYOUTS


test("window_tool", t_window_tool)


# ── Network Tool (structure) ───────────────────────────────────────────────────
def t_network_tool():
    from tools.network_tool import _FOCUS_PRESETS, _LUCIFEX_BLOCK_MARKER
    assert "deep_work" in _FOCUS_PRESETS
    assert len(_FOCUS_PRESETS["deep_work"]) > 5
    assert "lucifex" in _LUCIFEX_BLOCK_MARKER


test("network_tool", t_network_tool)


# ── AGI Tools registration ─────────────────────────────────────────────────────
def t_agi_tools():
    import tools.agi_tools  # triggers registration
    from tools.registry import registry
    all_tool_names = set(registry.get_all_tool_names())
    required = {"world_model_query", "goal_add", "goal_list", "pre_flight_simulate",
                "get_user_knowledge_model", "find_analogous_solution"}
    missing = required - all_tool_names
    assert not missing, f"Missing AGI tools: {missing}"


test("agi_tools_registration", t_agi_tools)


# ── Summary ────────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"  Result: {len(ok)}/{len(ok)+len(fail)} passed")
if fail:
    print(f"  Failed: {fail}")
print(f"{'='*50}\n")

if fail:
    sys.exit(1)
