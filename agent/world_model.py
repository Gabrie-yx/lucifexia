"""agent/world_model.py — Persistent causal knowledge graph for Lucifex.

Maintains a live graph of the user's world: projects, people, deadlines,
risks, and the causal relationships between them. Backed by SQLite with
NetworkX for in-memory graph operations.

This is the agent's persistent world model — not just memory of what was
said, but a structured understanding of how things relate and affect each
other. When one node changes, the agent can trace the impact cascade.

Node types: project, person, deadline, risk, concept, system, task
Edge types: blocks, depends_on, owned_by, related_to, causes, mitigates
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Optional

logger = logging.getLogger(__name__)

_lock = threading.RLock()
_db_path: Optional[Path] = None

NODE_TYPES = {"project", "person", "deadline", "risk", "concept", "system", "task", "event"}
EDGE_TYPES = {"blocks", "depends_on", "owned_by", "related_to", "causes", "mitigates", "precedes"}


def _get_db_path() -> Path:
    global _db_path
    if _db_path is None:
        try:
            from lucifex_constants import get_lucifex_home
            _db_path = Path(get_lucifex_home()) / "world_model.db"
        except Exception:
            _db_path = Path.home() / ".lucifex" / "world_model.db"
    return _db_path


@contextmanager
def _conn() -> Generator[sqlite3.Connection, None, None]:
    db = _get_db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        con = sqlite3.connect(db, check_same_thread=False)
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


def init_world_model() -> None:
    """Create world model tables. Idempotent."""
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS wm_nodes (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                node_type   TEXT NOT NULL,
                properties  TEXT DEFAULT '{}',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS wm_edges (
                id          TEXT PRIMARY KEY,
                source_id   TEXT NOT NULL,
                target_id   TEXT NOT NULL,
                edge_type   TEXT NOT NULL,
                weight      REAL DEFAULT 1.0,
                properties  TEXT DEFAULT '{}',
                created_at  TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES wm_nodes(id),
                FOREIGN KEY (target_id) REFERENCES wm_nodes(id)
            );

            CREATE INDEX IF NOT EXISTS idx_edges_source ON wm_edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON wm_edges(target_id);
            CREATE INDEX IF NOT EXISTS idx_nodes_type ON wm_nodes(node_type);
            CREATE VIRTUAL TABLE IF NOT EXISTS wm_nodes_fts USING fts5(
                id, name, node_type, properties
            );
        """)


def add_node(
    name: str,
    node_type: str,
    node_id: Optional[str] = None,
    properties: Optional[dict] = None,
) -> str:
    """Add or update a node. Returns the node ID."""
    import re
    if node_type not in NODE_TYPES:
        node_type = "concept"
    if node_id is None:
        node_id = re.sub(r"\W+", "_", name.lower())[:40]

    props_str = json.dumps(properties or {})
    now = _now()
    with _conn() as con:
        con.execute("""
            INSERT INTO wm_nodes (id, name, node_type, properties, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                properties=excluded.properties,
                updated_at=excluded.updated_at
        """, (node_id, name, node_type, props_str, now, now))
        # Sync FTS
        con.execute("DELETE FROM wm_nodes_fts WHERE id=?", (node_id,))
        con.execute(
            "INSERT INTO wm_nodes_fts(id, name, node_type, properties) VALUES(?,?,?,?)",
            (node_id, name, node_type, props_str),
        )
    logger.debug("World model node upserted: %s (%s)", name, node_type)
    return node_id


def add_edge(
    source_id: str,
    target_id: str,
    edge_type: str,
    weight: float = 1.0,
    properties: Optional[dict] = None,
) -> str:
    """Add a directed edge between two nodes."""
    import uuid
    if edge_type not in EDGE_TYPES:
        edge_type = "related_to"
    edge_id = str(uuid.uuid4())[:8]
    props_str = json.dumps(properties or {})
    with _conn() as con:
        # Remove existing edge of same type between same nodes
        con.execute(
            "DELETE FROM wm_edges WHERE source_id=? AND target_id=? AND edge_type=?",
            (source_id, target_id, edge_type),
        )
        con.execute("""
            INSERT INTO wm_edges (id, source_id, target_id, edge_type, weight, properties, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (edge_id, source_id, target_id, edge_type, weight, props_str, _now()))
    logger.debug("World model edge added: %s -[%s]-> %s", source_id, edge_type, target_id)
    return edge_id


def get_node(node_id: str) -> Optional[dict]:
    with _conn() as con:
        row = con.execute("SELECT * FROM wm_nodes WHERE id=?", (node_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["properties"] = json.loads(d.get("properties") or "{}")
        return d


def search_nodes(query: str, node_type: Optional[str] = None, limit: int = 10) -> list[dict]:
    """Full-text search over the world model."""
    with _conn() as con:
        if node_type:
            rows = con.execute(
                """SELECT n.* FROM wm_nodes n
                   JOIN wm_nodes_fts f ON n.id = f.id
                   WHERE wm_nodes_fts MATCH ? AND n.node_type=?
                   LIMIT ?""",
                (query, node_type, limit),
            ).fetchall()
        else:
            rows = con.execute(
                """SELECT n.* FROM wm_nodes n
                   JOIN wm_nodes_fts f ON n.id = f.id
                   WHERE wm_nodes_fts MATCH ?
                   LIMIT ?""",
                (query, limit),
            ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["properties"] = json.loads(d.get("properties") or "{}")
            result.append(d)
        return result


def get_impact_chain(node_id: str, edge_types: Optional[list] = None, depth: int = 4) -> dict:
    """Trace what is impacted if this node changes (BFS over outgoing edges)."""
    visited = {node_id}
    queue = [(node_id, 0)]
    chain = {"root": node_id, "impacts": []}

    with _conn() as con:
        while queue:
            current, level = queue.pop(0)
            if level >= depth:
                continue
            filter_clause = ""
            params: list = [current]
            if edge_types:
                placeholders = ",".join("?" * len(edge_types))
                filter_clause = f" AND e.edge_type IN ({placeholders})"
                params.extend(edge_types)

            rows = con.execute(
                f"""SELECT e.edge_type, e.weight, n.id, n.name, n.node_type
                    FROM wm_edges e JOIN wm_nodes n ON e.target_id = n.id
                    WHERE e.source_id=?{filter_clause}""",
                params,
            ).fetchall()

            for row in rows:
                target_id = row["id"]
                if target_id not in visited:
                    visited.add(target_id)
                    chain["impacts"].append({
                        "from": current,
                        "via": row["edge_type"],
                        "to": target_id,
                        "name": row["name"],
                        "type": row["node_type"],
                        "depth": level + 1,
                        "weight": row["weight"],
                    })
                    queue.append((target_id, level + 1))

    return chain


def get_critical_path(deadline_node_id: str) -> list[dict]:
    """Return nodes that block reaching a deadline, sorted by dependency depth."""
    with _conn() as con:
        blockers = con.execute("""
            SELECT n.id, n.name, n.node_type, n.properties
            FROM wm_edges e JOIN wm_nodes n ON e.source_id = n.id
            WHERE e.target_id=? AND e.edge_type IN ('blocks', 'depends_on', 'precedes')
            ORDER BY e.weight DESC
        """, (deadline_node_id,)).fetchall()
    return [dict(r) for r in blockers]


def extract_entities_from_text(text: str) -> dict:
    """Lightweight NLP extraction: find mentions of projects, people, dates."""
    import re
    entities = {"projects": [], "people": [], "deadlines": [], "risks": []}

    # People: capitalised names
    name_pattern = re.compile(r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b")
    entities["people"] = list(set(name_pattern.findall(text)))

    # Deadlines: date-like patterns
    date_pattern = re.compile(
        r"\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|"
        r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+\d{4})?)\b",
        re.IGNORECASE,
    )
    entities["deadlines"] = list(set(date_pattern.findall(text)))

    # Risks: phrases with risk keywords
    risk_pattern = re.compile(
        r"(?:risk|danger|might fail|could break|warning|critical|blocker)[^.]{0,80}", re.IGNORECASE
    )
    entities["risks"] = [m.group().strip() for m in risk_pattern.finditer(text)][:3]

    return entities


def auto_update_from_conversation(text: str, session_id: str = "") -> int:
    """Extract entities from conversation text and update the world model.

    Returns number of nodes/edges added.
    """
    init_world_model()
    entities = extract_entities_from_text(text)
    added = 0

    for person in entities["people"]:
        add_node(person, "person")
        added += 1

    for deadline in entities["deadlines"]:
        add_node(deadline, "deadline", properties={"raw": deadline, "session": session_id})
        added += 1

    for risk in entities["risks"]:
        add_node(risk[:60], "risk", properties={"description": risk, "session": session_id})
        added += 1

    return added


def export_to_mermaid() -> str:
    """Export the world model as a Mermaid graph diagram."""
    with _conn() as con:
        nodes = con.execute("SELECT id, name, node_type FROM wm_nodes LIMIT 50").fetchall()
        edges = con.execute(
            "SELECT source_id, target_id, edge_type FROM wm_edges LIMIT 100"
        ).fetchall()

    type_style = {
        "project": ":::project",
        "person": ":::person",
        "deadline": ":::deadline",
        "risk": ":::risk",
        "task": ":::task",
    }

    lines = ["graph LR"]
    for n in nodes:
        style = type_style.get(n["node_type"], "")
        safe_name = n["name"].replace('"', "'")
        lines.append(f'    {n["id"]}["{safe_name}"]')

    for e in edges:
        lines.append(f'    {e["source_id"]} -->|{e["edge_type"]}| {e["target_id"]}')

    return "\n".join(lines)


def write_mermaid_to_obsidian() -> Optional[str]:
    """Write the world model graph to Obsidian as a note with Mermaid diagram."""
    try:
        from tools.playbook_tool import _resolve_obsidian_vault_path
        vault = _resolve_obsidian_vault_path()
        out = vault / "WorldModel.md"
        diagram = export_to_mermaid()
        content = f"""---
title: World Model
updated: {_now()}
source: agent-world-model
---

# Lucifex World Model

```mermaid
{diagram}
```
"""
        out.write_text(content, encoding="utf-8")
        return str(out)
    except Exception as exc:
        logger.debug("Failed to write world model to Obsidian: %s", exc)
        return None
