"""tools/agi_tools.py — Model-facing tools for AGI capabilities.

Exposes the AGI subsystems as callable model tools:
  - world_model_query / world_model_add_node / world_model_add_edge
  - goal_add / goal_list / goal_progress / goal_project
  - simulate_action (pre-flight risk simulation)
  - get_prediction_cache_stats
  - get_user_mind_summary (theory of mind)
  - find_similar_patterns (isomorphism engine)
"""
from __future__ import annotations

import json
import logging

from tools.registry import registry

logger = logging.getLogger(__name__)


# ── World Model Tools ─────────────────────────────────────────────────────────

def world_model_query(query: str, node_type: str = "") -> str:
    """Search the agent's world model for nodes matching a query.

    The world model is a persistent causal graph of your projects, people,
    deadlines, risks, and dependencies. Use this to understand relationships
    and impact chains.
    """
    try:
        from agent.world_model import init_world_model, search_nodes, get_full_state
        init_world_model()
        if query == "*":
            # Return full state summary
            with_state: dict = {}
            from agent.world_model import _conn
            with _conn() as con:
                nodes = con.execute("SELECT id, name, node_type FROM wm_nodes LIMIT 30").fetchall()
                with_state["nodes"] = [dict(n) for n in nodes]
                edges = con.execute("SELECT source_id, target_id, edge_type FROM wm_edges LIMIT 50").fetchall()
                with_state["edges"] = [dict(e) for e in edges]
            return json.dumps(with_state, ensure_ascii=False)

        results = search_nodes(query, node_type=node_type or None, limit=10)
        return json.dumps(results, ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def world_model_add(name: str, node_type: str, properties: str = "{}") -> str:
    """Add a node to the world model.

    node_type: project | person | deadline | risk | concept | system | task | event
    properties: JSON string of additional attributes.
    """
    try:
        from agent.world_model import init_world_model, add_node
        init_world_model()
        props = json.loads(properties) if properties else {}
        node_id = add_node(name, node_type, properties=props)
        return json.dumps({"success": True, "id": node_id, "name": name, "type": node_type})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def world_model_connect(
    source_name: str,
    target_name: str,
    edge_type: str,
    weight: float = 1.0,
) -> str:
    """Connect two nodes in the world model with a typed edge.

    edge_type: blocks | depends_on | owned_by | related_to | causes | mitigates | precedes
    """
    try:
        from agent.world_model import init_world_model, search_nodes, add_edge
        import re
        init_world_model()

        def _find_or_create(name: str) -> str:
            results = search_nodes(name, limit=1)
            if results:
                return results[0]["id"]
            from agent.world_model import add_node
            return add_node(name, "concept")

        src_id = _find_or_create(source_name)
        tgt_id = _find_or_create(target_name)
        edge_id = add_edge(src_id, tgt_id, edge_type, weight)
        return json.dumps({"success": True, "edge_id": edge_id, "from": source_name, "to": target_name, "type": edge_type})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def world_model_impact(node_name: str) -> str:
    """Trace the impact chain: what is affected if this node changes?"""
    try:
        from agent.world_model import init_world_model, search_nodes, get_impact_chain
        init_world_model()
        results = search_nodes(node_name, limit=1)
        if not results:
            return json.dumps({"error": f"Node '{node_name}' not found in world model."})
        node = results[0]
        chain = get_impact_chain(node["id"])
        return json.dumps(chain, ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ── Goal Tools ────────────────────────────────────────────────────────────────

def goal_add(title: str, description: str = "", deadline: str = "") -> str:
    """Add a long-horizon goal for the agent to track across sessions.

    The agent will track progress, decompose it into milestones, and warn
    you if the pace suggests missing the deadline.
    """
    try:
        from agent.long_horizon import init_db, add_goal, decompose_goal_with_ai
        init_db()
        goal_id = add_goal(title, description, deadline or None)
        # Decompose asynchronously
        import threading
        t = threading.Thread(
            target=decompose_goal_with_ai, args=(goal_id,), daemon=True
        )
        t.start()
        return json.dumps({
            "success": True,
            "id": goal_id,
            "title": title,
            "deadline": deadline or None,
            "note": "Goal added. Milestones will be generated in background.",
        })
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def goal_list() -> str:
    """List all active long-horizon goals with current progress and projections."""
    try:
        from agent.long_horizon import init_db, get_active_goals, project_completion, get_milestones
        init_db()
        goals = get_active_goals()
        result = []
        for g in goals:
            proj = project_completion(g["id"])
            ms = get_milestones(g["id"])
            done_ms = sum(1 for m in ms if m.get("completed"))
            result.append({
                "id": g["id"],
                "title": g["title"],
                "progress": f"{float(g['progress']):.0%}",
                "milestones": f"{done_ms}/{len(ms)}",
                "projection": proj.get("message", ""),
                "deadline": g.get("deadline", "not set"),
            })
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def goal_log_progress(goal_id: str, delta: float, note: str = "") -> str:
    """Log incremental progress toward a goal (0.0 to 1.0 scale).

    delta: progress made (e.g. 0.1 = 10% done).
    """
    try:
        from agent.long_horizon import init_db, log_progress
        init_db()
        log_progress(goal_id, delta, note=note)
        return json.dumps({"success": True, "goal_id": goal_id, "delta": delta})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ── Simulation Tool ───────────────────────────────────────────────────────────

def pre_flight_simulate(action: str, context: str = "") -> str:
    """Simulate the outcomes of a potentially irreversible action before executing it.

    Returns probability distribution of outcomes, recommendation, and rollback plan.
    Use before: deployments, database migrations, bulk deletions, force-pushes.
    """
    try:
        from agent.simulator import simulate_action, format_simulation_for_user
        result = simulate_action(action, context)
        formatted = format_simulation_for_user(result)
        return json.dumps({
            "simulation_summary": formatted,
            "raw": result,
        }, ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ── Theory of Mind Tool ───────────────────────────────────────────────────────

def get_user_knowledge_model() -> str:
    """Return what the agent knows about the user's expertise and knowledge gaps.

    Includes: domain expertise levels, active misconceptions detected, explanation calibration.
    """
    try:
        from agent.theory_of_mind import get_mind_summary, get_explanation_calibration
        summary = get_mind_summary()
        return json.dumps(summary, ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ── Isomorphism Tool ──────────────────────────────────────────────────────────

def find_analogous_solution(problem_description: str) -> str:
    """Search the pattern library for solutions from other domains that map to this problem.

    The isomorphism engine finds structurally similar problems solved before and
    adapts their solutions to the current context.
    """
    try:
        from agent.isomorphism_engine import init_db, find_and_apply_best_pattern
        init_db()
        result = find_and_apply_best_pattern(problem_description)
        if not result:
            return json.dumps({"message": "No analogous pattern found in library yet."})
        return json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ── Registration ──────────────────────────────────────────────────────────────

_tools = [
    # World Model
    ("world_model_query", world_model_query,
     "Search the agent's causal world model for nodes (projects, people, deadlines, risks). Use '*' to see all.",
     {"query": {"type": "string"}, "node_type": {"type": "string"}}, ["query"]),
    ("world_model_add", world_model_add,
     "Add a node to the world model. Types: project, person, deadline, risk, concept, system, task, event.",
     {"name": {"type": "string"}, "node_type": {"type": "string"}, "properties": {"type": "string"}}, ["name", "node_type"]),
    ("world_model_connect", world_model_connect,
     "Connect two world model nodes. Edge types: blocks, depends_on, owned_by, related_to, causes, mitigates, precedes.",
     {"source_name": {"type": "string"}, "target_name": {"type": "string"},
      "edge_type": {"type": "string"}, "weight": {"type": "number"}}, ["source_name", "target_name", "edge_type"]),
    ("world_model_impact", world_model_impact,
     "Trace the causal impact chain: what is affected if this node/entity changes?",
     {"node_name": {"type": "string"}}, ["node_name"]),
    # Goals
    ("goal_add", goal_add,
     "Add a long-horizon goal for the agent to track across sessions. Milestones auto-generated.",
     {"title": {"type": "string"}, "description": {"type": "string"}, "deadline": {"type": "string"}}, ["title"]),
    ("goal_list", goal_list,
     "List all active long-horizon goals with progress, milestones, and completion projections.",
     {}, []),
    ("goal_log_progress", goal_log_progress,
     "Log progress toward a goal. delta is 0.0–1.0 (e.g. 0.1 = 10% done).",
     {"goal_id": {"type": "string"}, "delta": {"type": "number"}, "note": {"type": "string"}}, ["goal_id", "delta"]),
    # Simulation
    ("pre_flight_simulate", pre_flight_simulate,
     "Simulate outcomes of a risky/irreversible action before executing it. Returns probability distribution and rollback plan.",
     {"action": {"type": "string"}, "context": {"type": "string"}}, ["action"]),
    # Theory of Mind
    ("get_user_knowledge_model", get_user_knowledge_model,
     "Return what the agent knows about the user's expertise levels and any detected misconceptions.",
     {}, []),
    # Isomorphism
    ("find_analogous_solution", find_analogous_solution,
     "Search the cross-domain pattern library for solutions from other domains isomorphic to this problem.",
     {"problem_description": {"type": "string"}}, ["problem_description"]),
]

for _name, _fn, _desc, _props, _required in _tools:
    registry.register(
        name=_name,
        toolset="agi",
        schema={
            "name": _name,
            "description": _desc,
            "parameters": {"type": "object", "properties": _props, "required": _required},
        },
        handler=_fn,
        description=_desc,
        emoji="🧠",
    )


# ── Phase 3 Tool Functions (Features 27-33) ───────────────────────────────────

def run_specialist_panel(problem: str, solution: str, specialists: str = "") -> str:
    """Run a multi-specialist adversarial panel review on a proposed solution.

    Spawns specialist subagents in parallel: security, performance, maintainability,
    devil's advocate. Synthesizes findings into a final APPROVED / REJECTED verdict.
    specialists: comma-separated subset (security,performance,maintainability,devil).
    """
    try:
        from agent.parallel_arbitration import run_panel
        spec_list = [s.strip() for s in specialists.split(",")] if specialists else None
        result = run_panel(problem, solution, specialists=spec_list)
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def get_agent_evolution_stats() -> str:
    """Return the agent's self-evolution stats: quality signals, failure patterns, proposed prompt improvement."""
    try:
        from agent.self_evolution import get_quality_stats, generate_prompt_improvement
        stats = get_quality_stats()
        improvement = generate_prompt_improvement()
        return json.dumps({"quality_stats": stats, "proposed_improvement": improvement},
                          ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def get_active_commitments_tool() -> str:
    """Return all active decisions and commitments tracked across sessions."""
    try:
        from agent.commitment_tracker import get_active_commitments
        commitments = get_active_commitments(limit=20)
        return json.dumps({"commitments": commitments, "count": len(commitments)},
                          ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def supersede_commitment_tool(commitment_id: int, reason: str = "") -> str:
    """Mark a prior commitment as intentionally superseded — you changed your mind."""
    try:
        from agent.commitment_tracker import supersede_commitment
        supersede_commitment(commitment_id, reason)
        return json.dumps({"success": True, "commitment_id": commitment_id})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def get_cognitive_state() -> str:
    """Return the user's current cognitive load state and recommended communication style."""
    try:
        from agent.cognitive_load import get_state, get_peak_hours_analysis
        state = get_state()
        peaks = get_peak_hours_analysis()
        return json.dumps({"current_state": state, "peak_hours": peaks},
                          ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def get_project_ontology() -> str:
    """Return all concepts and terminology the agent has learned about this project."""
    try:
        from agent.ontology_builder import get_ontology_summary, get_context_prefix
        summary = get_ontology_summary()
        prefix = get_context_prefix(max_concepts=20)
        return json.dumps({"summary": summary, "context_prefix": prefix},
                          ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def trace_consequences(change_description: str, context: str = "", codebase_root: str = "") -> str:
    """Trace 2nd and 3rd order consequences of a proposed change.

    Analyses technical, human, process, and timeline impacts.
    codebase_root: path to codebase root for static analysis (optional).
    """
    try:
        from agent.consequence_engine import propagate_consequences, format_consequence_report
        result = propagate_consequences(
            description=change_description,
            context=context,
            codebase_root=codebase_root or None,
        )
        formatted = format_consequence_report(result)
        return json.dumps({"report": formatted, "raw": result}, ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def set_persona(persona_key: str, session_id: str = "") -> str:
    """Force the agent to adopt a specific persona for this session.

    Available: pythonista, architect, detective, product, explorer, mentor, critic.
    Use persona_key='list' to see all available personas.
    """
    try:
        from agent.persona_engine import force_persona, PERSONAS, list_personas
        if persona_key == "list":
            return json.dumps({"personas": list_personas()})
        ok = force_persona(persona_key, session_id)
        if ok:
            p = PERSONAS[persona_key]
            return json.dumps({"success": True, "persona": persona_key,
                               "name": p["name"], "style": p["style_hint"]})
        return json.dumps({"error": f"Unknown persona '{persona_key}'. Use 'list' to see available."})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def get_current_persona(session_id: str = "") -> str:
    """Return the agent's current active persona and communication style."""
    try:
        from agent.persona_engine import get_current_persona as _get
        persona = _get(session_id)
        if not persona:
            return json.dumps({"persona": "auto", "note": "Auto-detecting per message."})
        return json.dumps(persona, ensure_ascii=False, default=str)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ── Phase 3 Registration ──────────────────────────────────────────────────────

_phase3_tools = [
    ("run_specialist_panel", run_specialist_panel,
     "Run specialist subagents in parallel (security, performance, maintainability, devil) and synthesize a verdict.",
     {"problem": {"type": "string"}, "solution": {"type": "string"},
      "specialists": {"type": "string"}}, ["problem", "solution"]),
    ("get_agent_evolution_stats", get_agent_evolution_stats,
     "Return quality metrics, failure patterns, and proposed system prompt improvements.",
     {}, []),
    ("get_active_commitments_tool", get_active_commitments_tool,
     "Return all decisions and commitments tracked from past sessions.",
     {}, []),
    ("supersede_commitment_tool", supersede_commitment_tool,
     "Mark a prior commitment as intentionally superseded.",
     {"commitment_id": {"type": "integer"}, "reason": {"type": "string"}}, ["commitment_id"]),
    ("get_cognitive_state", get_cognitive_state,
     "Return the user's cognitive load state (peak/normal/fatigued/overloaded) and communication style recommendation.",
     {}, []),
    ("get_project_ontology", get_project_ontology,
     "Return all domain concepts and terminology the agent has learned from this project.",
     {}, []),
    ("trace_consequences", trace_consequences,
     "Trace 2nd and 3rd order consequences of a change across technical, human, process, and timeline dimensions.",
     {"change_description": {"type": "string"}, "context": {"type": "string"},
      "codebase_root": {"type": "string"}}, ["change_description"]),
    ("set_persona", set_persona,
     "Set active persona: pythonista, architect, detective, product, explorer, mentor, critic. Use 'list' to see all.",
     {"persona_key": {"type": "string"}, "session_id": {"type": "string"}}, ["persona_key"]),
    ("get_current_persona", get_current_persona,
     "Return the agent's current active persona and style configuration.",
     {"session_id": {"type": "string"}}, []),
]

for _name, _fn, _desc, _props, _required in _phase3_tools:
    registry.register(
        name=_name,
        toolset="agi",
        schema={
            "name": _name,
            "description": _desc,
            "parameters": {"type": "object", "properties": _props, "required": _required},
        },
        handler=_fn,
        description=_desc,
        emoji="⚡",
    )
