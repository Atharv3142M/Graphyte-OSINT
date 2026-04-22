"""
Thin Neo4j client for ingesting STIX-like objects into a queryable graph.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable

from neo4j import GraphDatabase, Driver


def _neo4j_safe_value(v: Any) -> Any:
    # Neo4j properties must be primitives or arrays of primitives.
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, (list, tuple)):
        if all(isinstance(x, (str, int, float, bool)) or x is None for x in v):
            return list(v)
        return json.dumps(v, ensure_ascii=False)[:100_000]
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)[:100_000]
    return str(v)[:10_000]


def _neo4j_safe_props(props: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in props.items():
        try:
            out[k] = _neo4j_safe_value(v)
        except Exception:
            out[k] = str(v)
    return out


class Neo4jClient:
    def __init__(self) -> None:
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "dev_neo4j_secret")
        timeout_s = float(os.getenv("NEO4J_CONNECT_TIMEOUT", "5"))
        self._driver: Driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            connection_timeout=timeout_s,
            max_connection_lifetime=60,
        )

    def close(self) -> None:
        self._driver.close()

    def ingest_bundle(self, bundle: Dict[str, Any]) -> None:
        """
        Ingest a minimal STIX bundle into Neo4j.

        Each object becomes a node with label `Stix` and an additional label
        for its type. Relationships (if present) are created for simple ref fields.
        """
        objects: Iterable[Dict[str, Any]] = bundle.get("objects", [])
        with self._driver.session() as session:
            for obj in objects:
                session.execute_write(_merge_object, obj)

    def get_graph_cytoscape(self, limit: int = 50) -> Dict[str, Any]:
        """
        Fetch all Stix nodes and relationships as Cytoscape elements format.
        Returns { elements: { nodes: [...], edges: [...] } }.
        """
        nodes_out: list[Dict[str, Any]] = []
        edges_out: list[Dict[str, Any]] = []
        with self._driver.session() as session:
            nodes_result = session.run("MATCH (n:Stix) RETURN n ORDER BY n.created DESC LIMIT $limit", limit=limit)
            for record in nodes_result:
                node = record["n"]
                if node is None:
                    continue
                stix_id = node.get("id") or str(node.element_id)
                stix_type = node.get("type") or "unknown"
                label = node.get("value") or node.get("abstract")
                if label is None and isinstance(node.get("content"), dict):
                    label = node.get("content", {}).get("abstract")
                if label is None:
                    label = stix_type
                label = str(label)[:80]
                nodes_out.append({
                    "data": {"id": stix_id, "label": label, "type": stix_type},
                    "classes": stix_type.replace("-", "_"),
                })
            edges_result = session.run(
                "MATCH (a:Stix)-[r]->(b:Stix) RETURN a.id AS src, b.id AS tgt, elementId(r) AS rid LIMIT $limit",
                limit=limit * 3
            )
            for record in edges_result:
                src = record.get("src")
                tgt = record.get("tgt")
                if src and tgt:
                    edges_out.append({
                        "data": {"id": f"e-{record.get('rid', len(edges_out))}", "source": src, "target": tgt},
                    })
        return {"elements": {"nodes": nodes_out, "edges": edges_out}}


def _merge_object(tx, obj: Dict[str, Any]) -> None:
    obj_id = obj.get("id")
    obj_type = obj.get("type")
    if not obj_id or not obj_type:
        return

    # Separate STIX properties from relationship fields
    relationship_fields = {"source_ref", "target_ref", "relationship_type", "created", "modified"}
    raw_props = {k: v for k, v in obj.items() if k not in {"id", "type"} and k not in relationship_fields}
    props = _neo4j_safe_props(raw_props)

    # Merge the node itself
    tx.run(
        """
        MERGE (n:Stix {id: $id})
        SET n.type = $type
        SET n += $props
        """,
        id=obj_id,
        type=obj_type,
        props=props,
    )

    # If this is a relationship object, create the directed edge
    if obj_type == "relationship":
        src = obj.get("source_ref")
        tgt = obj.get("target_ref")
        rel_type = obj.get("relationship_type", "related-to")
        if src and tgt:
            # Useapoc.create.rel to safely create dynamic relationship type
            safe_rel_type = rel_type.replace("-", "_").replace(":", "_")
            tx.run(
                f"""
                MATCH (a:Stix {{id: $src}}), (b:Stix {{id: $tgt}})
                MERGE (a)-[r:`{safe_rel_type}`]->(b)
                SET r.id = $rel_id
                """,
                src=src,
                tgt=tgt,
                rel_id=obj_id,
            )

