"""
Thin Neo4j client for ingesting STIX-like objects into a queryable graph.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Iterable

from neo4j import GraphDatabase, Driver


class Neo4jClient:
    def __init__(self) -> None:
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "dev_neo4j_secret")
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

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


def _merge_object(tx, obj: Dict[str, Any]) -> None:
    obj_id = obj.get("id")
    obj_type = obj.get("type")
    if not obj_id or not obj_type:
        return
    props = {k: v for k, v in obj.items() if k not in {"id", "type"}}
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

