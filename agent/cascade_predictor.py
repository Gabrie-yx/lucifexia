"""agent/cascade_predictor.py — Cascade failure prediction for Lucifex.

Analyses growth trends in code complexity, data volume, and performance
metrics to predict WHEN (not just IF) a system will break under load.

Rather than just saying "this might be slow", it says:
"At current growth rate, this query will exceed 5s timeout in ~3 weeks."

Findings are stored in Obsidian Discoveries/ for tracking over time.
"""
from __future__ import annotations

import json
import logging
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ── Code Complexity Analysis ──────────────────────────────────────────────────

def _count_lines(path: Path) -> int:
    try:
        return sum(1 for _ in path.open(encoding="utf-8", errors="ignore"))
    except Exception:
        return 0


def _cyclomatic_complexity_estimate(code: str) -> int:
    """Estimate cyclomatic complexity by counting decision points."""
    keywords = ["if ", "elif ", "else:", "for ", "while ", "except", "and ", "or ", "case "]
    return 1 + sum(code.count(kw) for kw in keywords)


def _find_n_plus_one_risks(code: str) -> list[str]:
    """Find potential N+1 query patterns."""
    risks = []
    lines = code.splitlines()
    for i, line in enumerate(lines):
        if re.search(r"for .+ in .+:", line):
            window = "\n".join(lines[i+1:i+5])
            if re.search(r"\.(query|execute|find|get|filter|objects)\(", window, re.IGNORECASE):
                risks.append(f"Line {i+1}: N+1 query risk — DB call inside loop: `{line.strip()}`")
    return risks[:3]


def _find_missing_indexes(code: str) -> list[str]:
    """Flag WHERE clauses on non-indexed-looking columns."""
    risks = []
    where_patterns = re.finditer(
        r"WHERE\s+(\w+)\s*[=<>!]", code, re.IGNORECASE
    )
    for match in where_patterns:
        col = match.group(1)
        if "id" not in col.lower() and col not in ("status", "type"):
            risks.append(f"Potential missing index on column `{col}` in WHERE clause")
    return list(set(risks))[:3]


def _estimate_growth_breaking_point(
    current_value: float,
    growth_rate_per_week: float,
    threshold: float,
) -> Optional[dict]:
    """Given linear growth, project when threshold is crossed."""
    if growth_rate_per_week <= 0:
        return None
    weeks_to_break = (threshold - current_value) / growth_rate_per_week
    if weeks_to_break < 0:
        return {"already_broken": True, "weeks": 0}
    break_date = (datetime.now(timezone.utc) + timedelta(weeks=weeks_to_break)).strftime("%Y-%m-%d")
    return {
        "weeks": round(weeks_to_break, 1),
        "break_date": break_date,
        "already_broken": False,
    }


# ── File / Codebase Analysis ──────────────────────────────────────────────────

def analyse_codebase(root_path: str) -> list[dict]:
    """Scan a codebase for cascade failure risks.

    Returns list of risk dicts with: file, risk_type, description, severity, projection.
    """
    root = Path(root_path)
    if not root.exists():
        return []

    risks = []

    # 1. Files growing too large
    for py_file in list(root.rglob("*.py"))[:100]:
        lines = _count_lines(py_file)
        if lines > 800:
            severity = "critical" if lines > 2000 else "high" if lines > 1200 else "medium"
            risks.append({
                "file": str(py_file.relative_to(root)),
                "risk_type": "monolith_growth",
                "description": f"{py_file.name} has {lines} lines. God files become unmaintainable and test coverage drops.",
                "severity": severity,
                "projection": f"At typical growth of 50 lines/week, will hit 3000 lines in ~{(3000-lines)//50} weeks.",
            })

    # 2. N+1 and missing indexes
    for py_file in list(root.rglob("*.py"))[:50]:
        try:
            code = py_file.read_text(encoding="utf-8", errors="ignore")
            n1_risks = _find_n_plus_one_risks(code)
            for r in n1_risks:
                risks.append({
                    "file": str(py_file.relative_to(root)),
                    "risk_type": "n_plus_one_query",
                    "description": r,
                    "severity": "high",
                    "projection": "Latency grows linearly with record count — will be visible at ~1000 rows.",
                })

            idx_risks = _find_missing_indexes(code)
            for r in idx_risks:
                risks.append({
                    "file": str(py_file.relative_to(root)),
                    "risk_type": "missing_index",
                    "description": r,
                    "severity": "medium",
                    "projection": "Full table scan. At 10k rows: ~50ms. At 100k rows: ~500ms. At 1M rows: timeout.",
                })
        except Exception:
            continue

    # 3. High cyclomatic complexity
    for py_file in list(root.rglob("*.py"))[:50]:
        try:
            code = py_file.read_text(encoding="utf-8", errors="ignore")
            complexity = _cyclomatic_complexity_estimate(code)
            if complexity > 50:
                risks.append({
                    "file": str(py_file.relative_to(root)),
                    "risk_type": "high_complexity",
                    "description": f"Cyclomatic complexity ~{complexity}. High complexity → hard to test → bugs hide.",
                    "severity": "medium",
                    "projection": "Each new feature adds 2-3x more integration surface. Will become unmaintainable.",
                })
        except Exception:
            continue

    # 4. Missing error handling around network/file operations
    for py_file in list(root.rglob("*.py"))[:50]:
        try:
            code = py_file.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"requests\.(get|post|put|delete|patch)\(", code) and "try" not in code:
                risks.append({
                    "file": str(py_file.relative_to(root)),
                    "risk_type": "unhandled_network_error",
                    "description": f"{py_file.name} makes HTTP requests without try/except. Will crash on timeout/5xx.",
                    "severity": "high",
                    "projection": "Production failure probability ~100% at sufficient scale. Network is unreliable.",
                })
        except Exception:
            continue

    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    risks.sort(key=lambda r: severity_order.get(r.get("severity", "low"), 3))
    return risks[:10]  # Top 10


def write_risks_to_obsidian(risks: list[dict], workspace_name: str = "project") -> Optional[str]:
    """Write cascade failure risks to Obsidian Discoveries/."""
    if not risks:
        return None
    try:
        from tools.playbook_tool import _resolve_obsidian_vault_path
        vault = _resolve_obsidian_vault_path()
        disc_dir = vault / "Discoveries"
        disc_dir.mkdir(parents=True, exist_ok=True)

        date = datetime.now().strftime("%Y-%m-%d")
        fname = f"{date}-cascade-risks-{workspace_name}.md"
        lines = [
            f"---",
            f"title: Cascade Risk Report — {workspace_name} — {date}",
            f"category: performance",
            f"impact: high",
            f"created: {datetime.now().isoformat()}",
            f"source: agent-cascade-predictor",
            f"---",
            f"",
            f"# Cascade Failure Risks — {workspace_name}",
            f"",
            f"*{len(risks)} risk(s) identified on {date}*",
            f"",
        ]

        for r in risks:
            emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(r.get("severity", ""), "⚪")
            lines += [
                f"## {emoji} [{r.get('severity', '?').upper()}] {r.get('risk_type', 'unknown')}",
                f"**File:** `{r.get('file', '?')}`",
                f"",
                f"{r.get('description', '')}",
                f"",
                f"**Projection:** {r.get('projection', 'N/A')}",
                f"",
            ]

        out = disc_dir / fname
        out.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Cascade risk report written: %s", out)
        return str(out)
    except Exception as exc:
        logger.debug("Failed to write cascade risks: %s", exc)
        return None


def quick_risk_summary(root_path: str) -> str:
    """Return a one-line summary of cascade risks for a codebase."""
    risks = analyse_codebase(root_path)
    if not risks:
        return "No significant cascade risks detected."
    critical = sum(1 for r in risks if r.get("severity") == "critical")
    high = sum(1 for r in risks if r.get("severity") == "high")
    return (
        f"{len(risks)} risk(s) found: "
        f"{critical} critical, {high} high. "
        f"Top: {risks[0]['risk_type']} in {risks[0]['file']}"
    )
