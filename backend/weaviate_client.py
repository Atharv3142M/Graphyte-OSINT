"""
Weaviate vector database client for semantic search.
Uses custom vectors (embedding model runs in Python); cosine similarity search.
"""
from __future__ import annotations

import os
from typing import Any


def _connect():
    import weaviate
    url = os.getenv("WEAVIATE_HTTP_URI", "http://localhost:8080")
    host = url.replace("http://", "").replace("https://", "").split(":")[0] or "127.0.0.1"
    port = 8080
    if ":" in url.split("//")[-1]:
        try:
            port = int(url.split(":")[-1].split("/")[0])
        except ValueError:
            pass
    return weaviate.connect_to_local(host=host, port=port)


def ensure_schema(client) -> None:
    """Create collection if it does not exist."""
    import weaviate.classes as wvc
    if client.collections.exists("OSINTDocument"):
        return
    client.collections.create(
        "OSINTDocument",
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
        properties=[
            wvc.config.Property(name="content", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="source_url", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="chunk_strategy", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="named_entities", data_type=wvc.config.DataType.TEXT_ARRAY),
        ],
    )


def add_documents(client, documents: list[dict[str, Any]], vectors: list[list[float]]) -> int:
    """Add documents with precomputed vectors."""
    import weaviate.classes as wvc
    coll = client.collections.get("OSINTDocument")
    objs = [
        wvc.data.DataObject(
            properties={
                "content": d.get("content", ""),
                "source_url": d.get("source_url", ""),
                "chunk_strategy": d.get("chunk_strategy", ""),
                "named_entities": d.get("named_entities", []),
            },
            vector=vec,
        )
        for d, vec in zip(documents, vectors)
    ]
    coll.data.insert_many(objs)
    return len(documents)


def semantic_search(client, query_vector: list[float], limit: int = 10) -> list[dict[str, Any]]:
    """Cosine similarity search."""
    coll = client.collections.get("OSINTDocument")
    results = coll.query.near_vector(
        near_vector=query_vector,
        limit=limit,
        return_metadata=["distance"],
    )
    out = []
    for obj in results.objects:
        out.append({
            "content": obj.properties.get("content"),
            "source_url": obj.properties.get("source_url"),
            "chunk_strategy": obj.properties.get("chunk_strategy"),
            "named_entities": obj.properties.get("named_entities") or [],
            "distance": float(obj.metadata.distance) if obj.metadata and obj.metadata.distance is not None else None,
        })
    return out
