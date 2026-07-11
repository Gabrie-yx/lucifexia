"""agent/consequence_engine.py — 2nd & 3rd Order Consequence Propagation. (Feature 32)

Before any change, traces ALL consequences across technical, human, and
process dimensions to 3 levels deep.

"Renaming this function" → breaks 12 call sites → breaks CI/CD test →
blocks João's PR → delays sprint delivery → triggers a client escalation.

Consequence graph is built via static analysis + AI reasoning.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ── Static Analysis ────────────────────────────────────────────────────────────

def _find_function_usages(function_name: str, root: Path) -> list[dict]:
    """Find all usages of a function across the codebase."""
    try:
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", function_name, str(root)],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode not in (0, 1):
            # Fallback: Python ripgrep style
            return []
        usages = []
        for line in result.stdout.splitlines()[:30]:
            parts = line.split(":", 2)
            if len(parts) >= 3:
                usages.append({
                    "file": parts[0],
                    "line": parts[1],
                    "content": parts[2].strip()[:100],
                })
        return usages
    except Exception:
        return []


def _find_function_usages_windows(function_name: str, root: Path) -> list[dict]:
    """Windows-compatible function usage search."""
    usages = []
    try:
        for py_file in list(root.rglob("*.py"))[:200]:
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                for i, line in enumerate(content.splitlines(), 1):
                    if function_name in line and not line.strip().startswith("#"):
                        usages.append({
                            "file": str(py_file.relative_to(root)),
                            "line": str(i),
                            "content": line.strip()[:100],
                        })
                        if len(usages) >= 20:
                            return usages
            except Exception:
                continue
    except Exception:
        pass
    return usages


def _detect_change_type(description: str) -> str:
    """Classify the type of change being proposed."""
    desc_lower = description.lower()
    if any(k in desc_lower for k in ["rename", "move", "extract", "refactor"]):
        return "structural"
    if any(k in desc_lower for k in ["delete", "remove", "drop", "deprecate"]):
        return "destructive"
    if any(k in desc_lower for k in ["add", "create", "introduce", "implement"]):
        return "additive"
    if any(k in desc_lower for k in ["change", "modify", "update", "alter"]):
        return "mutating"
    return "unknown"


# ── Consequence Graph ─────────────────────────────────────────────────────────

def _build_static_consequences(
    description: str,
    file_path: Optional[str] = None,
    codebase_root: Optional[str] = None,
) -> list[dict]:
    """Build the first layer of consequences via static analysis."""
    consequences = []
    change_type = _detect_change_type(description)

    # Extract entity being changed
    entity_match = re.search(r"(?:rename|delete|remove|refactor|change)\s+(?:function|method|class|module|file)?\s*['\"]?(\w+)['\"]?", description, re.IGNORECASE)
    entity_name = entity_match.group(1) if entity_match else None

    if entity_name and codebase_root:
        root = Path(codebase_root)
        if root.exists():
            usages = _find_function_usages_windows(entity_name, root)
            if usages:
                consequences.append({
                    "order": 1,
                    "type": "code_impact",
                    "description": f"'{entity_name}' is referenced in {len(usages)} location(s)",
                    "files_affected": list({u["file"] for u in usages}),
                    "severity": "high" if len(usages) > 5 else "medium",
                    "examples": [u["content"] for u in usages[:3]],
                })

                # Infer second-order: tests
                test_files = [u for u in usages if "test" in u["file"].lower()]
                if test_files:
                    consequences.append({
                        "order": 2,
                        "type": "test_impact",
                        "description": f"{len(test_files)} test(s) will fail — CI/CD pipeline blocked",
                        "severity": "high",
                        "files_affected": [u["file"] for u in test_files],
                    })

    # Additive changes: check for naming conflicts
    if change_type == "additive" and entity_name and codebase_root:
        root = Path(codebase_root)
        if root.exists():
            conflicts = [
                str(f) for f in root.rglob(f"*{entity_name}*")
                if f.is_file()
            ]
            if conflicts:
                consequences.append({
                    "order": 1,
                    "type": "naming_conflict",
                    "description": f"Files/symbols named '{entity_name}' already exist",
                    "severity": "medium",
                    "files_affected": conflicts[:5],
                })

    return consequences


def propagate_consequences(
    description: str,
    context: str = "",
    file_path: Optional[str] = None,
    codebase_root: Optional[str] = None,
    max_orders: int = 3,
) -> dict:
    """Trace consequences of a change to N orders deep.

    Returns {
        "change": str,
        "change_type": str,
        "consequences": [{"order": 1|2|3, "type": ..., "description": ..., "severity": ...}],
        "risk_score": float,
        "recommended_sequence": str,
    }
    """
    change_type = _detect_change_type(description)
    static_consequences = _build_static_consequences(description, file_path, codebase_root)

    # AI-powered deeper consequence analysis
    ai_consequences = _ai_consequence_analysis(description, context, static_consequences, max_orders)

    all_consequences = static_consequences + ai_consequences
    risk_score = _compute_risk_score(all_consequences)

    return {
        "change": description,
        "change_type": change_type,
        "consequences": all_consequences,
        "consequence_count": len(all_consequences),
        "risk_score": round(risk_score, 2),
        "risk_label": "critical" if risk_score > 0.7 else "high" if risk_score > 0.4 else "medium" if risk_score > 0.2 else "low",
        "recommended_sequence": _suggest_sequence(description, all_consequences),
    }


def _ai_consequence_analysis(
    description: str,
    context: str,
    known_consequences: list,
    max_orders: int,
) -> list[dict]:
    """Use AI to reason about 2nd and 3rd order consequences."""
    try:
        from agent.oneshot import run_oneshot
        known_str = ""
        if known_consequences:
            known_str = "Known 1st-order consequences:\n" + "\n".join(
                f"- {c['description']}" for c in known_consequences
            )

        prompt = (
            f"Trace the consequences of this change to {max_orders} levels deep.\n\n"
            f"Change: {description}\n"
            f"Context: {context[:300] if context else 'none'}\n"
            f"{known_str}\n\n"
            f"For each consequence, specify the order (1=direct, 2=second-order, 3=third-order) "
            f"and the dimension (technical, human, process, business, timeline).\n\n"
            f"Return a JSON array of consequences:\n"
            f'[{{"order": 2, "type": "process", "description": "...", "severity": "high|medium|low"}}]'
        )
        result = run_oneshot(prompt, max_tokens=450)
        if not result:
            return []
        match = re.search(r"\[.*\]", result, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return [c for c in data if isinstance(c, dict)][:8]
    except Exception as exc:
        logger.debug("AI consequence analysis failed: %s", exc)
    return []


def _compute_risk_score(consequences: list[dict]) -> float:
    severity_weights = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.1}
    order_weights = {1: 1.0, 2: 0.6, 3: 0.3}
    if not consequences:
        return 0.1
    total = sum(
        severity_weights.get(c.get("severity", "low"), 0.1)
        * order_weights.get(c.get("order", 1), 0.3)
        for c in consequences
    )
    return min(1.0, total / max(len(consequences), 1))


def _suggest_sequence(description: str, consequences: list) -> str:
    """Suggest the safest order of operations to minimise disruption."""
    steps = ["1. Run full test suite before making any changes"]
    if any("test" in c.get("type", "") for c in consequences):
        steps.append("2. Update tests FIRST to accept both old and new behaviour (expand-contract)")
    if any("naming" in c.get("type", "") for c in consequences):
        steps.append("3. Resolve naming conflicts before introducing the change")
    steps.append(f"4. Apply: {description[:80]}")
    steps.append("5. Verify: run tests, check affected files, review CI/CD")
    return "\n".join(steps)


def format_consequence_report(result: dict) -> str:
    """Format consequence analysis as a human-readable message."""
    lines = [
        f"🌊 **Consequence Map** — Risk: {result['risk_label'].upper()} ({result['risk_score']:.0%})\n",
        f"**Change:** {result['change'][:100]}\n",
        f"**{result['consequence_count']} consequence(s) identified:**\n",
    ]
    by_order = {}
    for c in result.get("consequences", []):
        o = c.get("order", 1)
        by_order.setdefault(o, []).append(c)

    order_names = {1: "Direct", 2: "2nd Order", 3: "3rd Order"}
    for order in sorted(by_order):
        lines.append(f"**{order_names.get(order, f'Order {order}')}:**")
        for c in by_order[order]:
            sev = c.get("severity", "?")
            emoji = {"high": "🔴", "critical": "💀", "medium": "🟡", "low": "🟢"}.get(sev, "⚪")
            lines.append(f"  {emoji} {c.get('description', '')}")
        lines.append("")

    seq = result.get("recommended_sequence", "")
    if seq:
        lines.append(f"**Recommended sequence:**\n{seq}")
    return "\n".join(lines)
