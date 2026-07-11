"""scratch/test_phase3.py — Phase 3 (Features 27-33) validation suite."""
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ok, fail = [], []


def test(name, fn):
    try:
        fn()
        ok.append(name)
        print(f"  [PASS] {name}")
    except Exception as e:
        fail.append(name)
        print(f"  [FAIL] {name}: {e}")
        import traceback; traceback.print_exc()


# ── 27: Parallel Arbitration ──────────────────────────────────────────────────
def t27():
    from agent.parallel_arbitration import SPECIALISTS, should_use_panel
    assert "security" in SPECIALISTS and "devil" in SPECIALISTS
    long_solution = " ".join(["implementation"] * 90)
    assert should_use_panel("database schema design and architecture", long_solution)
    assert not should_use_panel("hello", "hi")


test("27_parallel_arbitration", t27)


# ── 28: Self Evolution ────────────────────────────────────────────────────────
def t28():
    from agent.self_evolution import init_db, score_turn, get_quality_stats
    init_db()
    s1 = score_turn("thank you, perfect solution!", "test")
    assert s1 == 1.0, f"expected 1.0 got {s1}"
    s2 = score_turn("no that is wrong, try again", "test")
    assert s2 == -1.0, f"expected -1.0 got {s2}"
    s3 = score_turn("ok continue", "test")
    assert s3 == 0.0, f"expected 0.0 got {s3}"
    stats = get_quality_stats()
    assert "success_rate" in stats
    assert stats["successes"] >= 1


test("28_self_evolution", t28)


# ── 29: Commitment Tracker ────────────────────────────────────────────────────
def t29():
    from agent.commitment_tracker import (
        init_db, extract_and_store_commitments, get_active_commitments,
        _extract_tech_keywords,
    )
    init_db()
    text = "We will use PostgreSQL for all data storage. We decided to avoid Redis."
    n = extract_and_store_commitments(text, session_id="t29")
    assert n > 0, "no commitments extracted"
    commitments = get_active_commitments()
    assert len(commitments) > 0
    kw = _extract_tech_keywords("switch to mongodb instead of postgres")
    assert "mongodb" in kw


test("29_commitment_tracker", t29)


# ── 30: Cognitive Load ────────────────────────────────────────────────────────
def t30():
    from agent.cognitive_load import init_db, analyse_message, compute_load_score, get_state, STATES
    init_db()
    msg = "how does this work? why isnt it working? what should I do now?"
    sig = analyse_message(msg, "test")
    assert sig["word_count"] > 0
    assert sig["question_density"] > 0
    score = compute_load_score("test")
    assert 0.0 <= score <= 1.0
    state = get_state("test")
    assert state["state"] in STATES
    assert "style_hint" in state


test("30_cognitive_load", t30)


# ── 31: Ontology Builder ──────────────────────────────────────────────────────
def t31():
    from agent.ontology_builder import (
        init_db, extract_and_store_concepts, get_ontology_summary, find_concept,
    )
    init_db()
    text = "The gateway is the component that routes messages from external platforms to the agent core."
    n = extract_and_store_concepts(text, "test")
    assert n > 0, f"no concepts extracted from: {text}"
    summary = get_ontology_summary()
    assert summary["total_concepts"] > 0


test("31_ontology_builder", t31)


# ── 32: Consequence Engine ────────────────────────────────────────────────────
def t32():
    from agent.consequence_engine import (
        _detect_change_type, _compute_risk_score, propagate_consequences,
    )
    assert _detect_change_type("rename function foo") == "structural"
    assert _detect_change_type("delete the users table") == "destructive"
    assert _detect_change_type("add a new endpoint") == "additive"

    cons = [{"severity": "high", "order": 1}, {"severity": "medium", "order": 2}]
    score = _compute_risk_score(cons)
    assert 0 < score <= 1.0

    result = propagate_consequences(
        "rename function process_payment",
        context="payment module",
    )
    assert "change_type" in result
    assert "consequences" in result
    assert "risk_score" in result


test("32_consequence_engine", t32)


# ── 33: Persona Engine ────────────────────────────────────────────────────────
def t33():
    from agent.persona_engine import (
        init_db, detect_persona, force_persona, get_current_persona,
        list_personas, PERSONAS, release_forced_persona,
    )
    init_db()
    p = detect_persona("I have a bug in my python code, exception thrown", session_id="t33")
    assert p in PERSONAS, f"detected persona '{p}' not in PERSONAS"

    ok = force_persona("architect", "t33")
    assert ok

    current = get_current_persona("t33")
    assert current["key"] == "architect"

    personas = list_personas()
    assert len(personas) == len(PERSONAS)

    release_forced_persona("t33")


test("33_persona_engine", t33)


# ── Phase 3 Tool Registration ─────────────────────────────────────────────────
def t_reg():
    import tools.agi_tools  # triggers registration
    from tools.registry import registry
    names = set(registry.get_all_tool_names())
    required = {
        "run_specialist_panel",
        "get_agent_evolution_stats",
        "get_active_commitments_tool",
        "get_cognitive_state",
        "get_project_ontology",
        "trace_consequences",
        "set_persona",
        "get_current_persona",
    }
    missing = required - names
    assert not missing, f"Missing tools: {missing}"


test("phase3_tools_registered", t_reg)


# ── Summary ────────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"  Phase 3: {len(ok)}/{len(ok)+len(fail)} passed")
if fail:
    print(f"  Failed: {fail}")
print(f"{'='*50}\n")

if fail:
    sys.exit(1)
