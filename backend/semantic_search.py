"""
Semantic search service: embed query -> Weaviate near_vector.
"""
from __future__ import annotations


def _embed(text: str) -> list[float]:
    from backend.modules.graysentinel_pipeline import get_embedder
    model = get_embedder()
    return model.encode([text])[0].tolist()


def search(query: str, limit: int = 10) -> list[dict]:
    """Natural language query -> cosine similarity search -> contextual documents."""
    from backend.weaviate_client import _connect, semantic_search
    vec = _embed(query)
    client = _connect()
    try:
        return semantic_search(client, vec, limit=limit)
    finally:
        client.close()
