"""agent/simulator.py — Counterfactual Simulator for Lucifex.

Before executing irreversible actions (deploys, migrations, deletions,
destructive shell commands), the agent simulates possible outcomes and
presents a probability distribution to the user.

Learns from past predictions vs. actual outcomes to calibrate accuracy
over time. Predictions and outcomes stored in SQLite.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_lock = threading.RLock()
_db_path: Optional[Path] = None

# Commands that are considered irreversible and warrant simulation
_HIGH_RISK_PATTERNS = [
    r"DROP TABLE|DROP DATABASE|DELETE FROM|TRUNCATE",
    r"rm -rf|rmdir /s|del /f",
    r"kubectl delete|helm uninstall",
    r"git push --force|git reset --hard",
    r"ALTER TABLE.*DROP|RENAME TABLE",
    r"migrate|migration|schema.change",
    r"deploy|deployment|release",
    r"chmod -R|chown -R",
]

_COMPILED_RISKS = [re.compile(p, re.IGNORECASE) for p in _HIGH_RISK_PATTERNS]


def _get_db() -> Path:
    global _db_path
    if _db_path is None:
        try:
            from lucifex_constants import get_lucifex_home
            _db_path = Path(get_lucifex_home()) / "simulations.db"
        except Exception:
            _db_path = Path.home() / ".lucifex" / "simulations.db"
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    return _db_path


@contextmanager
def _conn():
    with _lock:
        con = sqlite3.connect(_get_db(), check_same_thread=False)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS simulations (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                action          TEXT NOT NULL,
                context         TEXT,
                predicted_outcomes TEXT,
                confidence      REAL,
                actual_outcome  TEXT,
                was_correct     INTEGER,
                session_id      TEXT,
                simulated_at    TEXT NOT NULL
            );
        """)


# ── Risk Assessment ───────────────────────────────────────────────────────────

def is_high_risk(action: str) -> bool:
    """Determine if an action is high-risk and warrants simulation."""
    return any(p.search(action) for p in _COMPILED_RISKS)


def _classify_risk_level(action: str) -> str:
    """Classify the risk level of an action."""
    action_lower = action.lower()
    if any(kw in action_lower for kw in ["drop", "delete", "rm -rf", "truncate", "force"]):
        return "critical"
    if any(kw in action_lower for kw in ["migrate", "deploy", "release", "alter table"]):
        return "high"
    if any(kw in action_lower for kw in ["chmod", "chown", "rename", "move"]):
        return "medium"
    return "low"


# ── Simulation ────────────────────────────────────────────────────────────────

def simulate_action(
    action: str,
    context: str = "",
    session_id: str = "",
) -> dict:
    """Simulate possible outcomes of an action before execution.

    Returns a distribution of likely outcomes with probabilities.
    """
    init_db()
    risk_level = _classify_risk_level(action)

    # Get calibration from historical accuracy
    calibration = _get_calibration()

    try:
        from agent.oneshot import run_oneshot

        # Check for similar past simulations
        similar = _find_similar_simulations(action)
        history_context = ""
        if similar:
            history_context = f"\nRelevant past execution outcomes:\n" + "\n".join(
                f"- Action: {s['action'][:60]} → Outcome: {s.get('actual_outcome', 'unknown')}"
                for s in similar[:2]
            )

        prompt = f"""You are simulating the outcomes of a potentially irreversible action.

Action to simulate: {action}
Context: {context[:400] if context else 'none'}
Risk level: {risk_level}
{history_context}

Analyse this action and provide a JSON response with:
{{
  "outcomes": [
    {{"scenario": "Success", "probability": 0.75, "description": "What happens if it works", "impact": "What changes permanently"}},
    {{"scenario": "Partial failure", "probability": 0.15, "description": "What breaks partially", "rollback": "How to recover"}},
    {{"scenario": "Full failure", "probability": 0.10, "description": "Worst case", "rollback": "How to recover or if it's unrecoverable"}}
  ],
  "recommendation": "Proceed | Proceed with caution | Do not proceed",
  "prerequisites": ["List of things to verify before executing"],
  "rollback_plan": "How to undo if it goes wrong"
}}

Be specific to the actual action. Use realistic probabilities that sum to 1.0."""

        result = run_oneshot(prompt, max_tokens=500)
        simulation_data = {"raw": result}

        if result:
            match = re.search(r"\{.*\}", result, re.DOTALL)
            if match:
                try:
                    simulation_data = json.loads(match.group())
                except json.JSONDecodeError:
                    simulation_data = {"raw": result}

    except Exception as exc:
        logger.debug("Simulation model call failed: %s", exc)
        simulation_data = _heuristic_simulation(action, risk_level)

    # Persist simulation
    try:
        with _conn() as con:
            con.execute("""
                INSERT INTO simulations (action, context, predicted_outcomes, confidence, session_id, simulated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                action[:500],
                context[:300],
                json.dumps(simulation_data),
                calibration.get("accuracy", 0.5),
                session_id,
                _now(),
            ))
    except Exception as exc:
        logger.debug("Failed to persist simulation: %s", exc)

    return {
        "action": action,
        "risk_level": risk_level,
        "simulation": simulation_data,
        "historical_accuracy": f"{calibration.get('accuracy', 50):.0%}",
    }


def _heuristic_simulation(action: str, risk_level: str) -> dict:
    """Fallback simulation when AI is unavailable."""
    base_success = {"critical": 0.60, "high": 0.75, "medium": 0.85, "low": 0.95}.get(risk_level, 0.75)
    return {
        "outcomes": [
            {"scenario": "Success", "probability": base_success, "description": "Action completes as intended."},
            {"scenario": "Partial failure", "probability": round((1 - base_success) * 0.6, 2),
             "description": "Action partially succeeds; some components may need manual correction."},
            {"scenario": "Full failure", "probability": round((1 - base_success) * 0.4, 2),
             "description": "Action fails entirely; manual recovery required."},
        ],
        "recommendation": "Proceed with caution" if risk_level in ("critical", "high") else "Proceed",
        "prerequisites": ["Verify you have a recent backup", "Test in staging first if possible"],
        "rollback_plan": "Restore from most recent backup.",
    }


def _find_similar_simulations(action: str, limit: int = 3) -> list[dict]:
    """Find past simulations of similar actions."""
    words = action.split()[:5]
    with _conn() as con:
        results = []
        for word in words:
            if len(word) > 4:
                rows = con.execute(
                    "SELECT * FROM simulations WHERE action LIKE ? AND actual_outcome IS NOT NULL ORDER BY id DESC LIMIT 2",
                    (f"%{word}%",),
                ).fetchall()
                results.extend([dict(r) for r in rows])
        # Deduplicate by id
        seen = set()
        unique = []
        for r in results:
            if r["id"] not in seen:
                seen.add(r["id"])
                unique.append(r)
        return unique[:limit]


def _get_calibration() -> dict:
    """Calculate historical simulation accuracy."""
    with _conn() as con:
        total = con.execute(
            "SELECT COUNT(*) FROM simulations WHERE was_correct IS NOT NULL"
        ).fetchone()[0]
        correct = con.execute(
            "SELECT COUNT(*) FROM simulations WHERE was_correct=1"
        ).fetchone()[0]
    accuracy = (correct / total) if total > 0 else 0.5
    return {"total": total, "correct": correct, "accuracy": accuracy}


def record_actual_outcome(simulation_id: int, outcome: str, was_correct: bool) -> None:
    """Record what actually happened after a simulated action."""
    init_db()
    with _conn() as con:
        con.execute(
            "UPDATE simulations SET actual_outcome=?, was_correct=? WHERE id=?",
            (outcome, 1 if was_correct else 0, simulation_id),
        )


def get_simulation_accuracy() -> str:
    """Return the agent's historical simulation accuracy as a human-readable string."""
    cal = _get_calibration()
    if cal["total"] == 0:
        return "No simulation history yet."
    return (
        f"Historical accuracy: {cal['accuracy']:.0%} "
        f"({cal['correct']}/{cal['total']} predictions correct)"
    )


def format_simulation_for_user(simulation_result: dict) -> str:
    """Format a simulation result as a readable message for the user."""
    sim = simulation_result.get("simulation", {})
    action = simulation_result.get("action", "")
    risk = simulation_result.get("risk_level", "unknown")
    accuracy = simulation_result.get("historical_accuracy", "unknown")

    lines = [
        f"⚡ **Pre-execution Simulation** (risk: {risk.upper()}, my historical accuracy: {accuracy})\n",
        f"**Action:** `{action[:100]}`\n",
        "**Predicted outcomes:**",
    ]

    for outcome in sim.get("outcomes", []):
        pct = int(float(outcome.get("probability", 0)) * 100)
        lines.append(f"- {pct}% — **{outcome.get('scenario', '?')}**: {outcome.get('description', '')}")

    rec = sim.get("recommendation", "")
    if rec:
        emoji = "✅" if "Proceed" == rec else "⚠️" if "caution" in rec else "🛑"
        lines.append(f"\n{emoji} **Recommendation:** {rec}")

    rollback = sim.get("rollback_plan", "")
    if rollback:
        lines.append(f"\n🔄 **Rollback plan:** {rollback}")

    prereqs = sim.get("prerequisites", [])
    if prereqs:
        lines.append("\n**Before proceeding:**")
        for p in prereqs:
            lines.append(f"- {p}")

    return "\n".join(lines)
