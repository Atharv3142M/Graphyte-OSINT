"""
GraySentinel extraction pipeline for deep-web literature.
Scrapes URLs, chunks text (by-title, similarity-based, context-aware),
extracts named entities, generates embeddings, stores in Weaviate.
"""
from __future__ import annotations

import re
from typing import Any

# Named-entity patterns (GraySentinel-style; ML-optimized regex)
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
IPV4_RE = re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b")
DOMAIN_RE = re.compile(r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b")
PHONE_RE = re.compile(r"\+?[1-9][0-9]{7,14}\b")


def extract_named_entities(text: str) -> list[str]:
    """Extract emails, IPs, domains, phones from text."""
    entities: set[str] = set()
    for pat in (EMAIL_RE, IPV4_RE, DOMAIN_RE, PHONE_RE):
        entities.update(pat.findall(text))
    return list(entities)[:50]


def chunk_by_title(text: str, source_url: str = "") -> list[dict[str, Any]]:
    """Split by markdown/HTML-style headers (##, ###, <h2>, etc.)."""
    parts = re.split(r"(?:\n#{1,6}\s+|\n(?=====+|\n-{3,}\s*\n))", text)
    chunks = []
    for i, p in enumerate(parts):
        p = p.strip()
        if len(p) < 30:
            continue
        entities = extract_named_entities(p)
        chunks.append({
            "content": p[:8000],
            "source_url": source_url,
            "chunk_strategy": "chunk_by_title",
            "named_entities": entities,
        })
    return chunks


def chunk_similarity_based(text: str, source_url: str = "", size: int = 512, overlap: int = 64) -> list[dict[str, Any]]:
    """Sliding window with overlap (sentence-boundary aware where possible)."""
    words = text.split()
    chunks = []
    start = 0
    idx = 0
    while start < len(words):
        end = min(start + size, len(words))
        block = " ".join(words[start:end])
        if len(block.strip()) >= 50:
            entities = extract_named_entities(block)
            chunks.append({
                "content": block,
                "source_url": source_url,
                "chunk_strategy": "similarity_based",
                "named_entities": entities,
            })
            idx += 1
        start = end - overlap
        if start >= len(words):
            break
    return chunks


def chunk_context_aware(text: str, source_url: str = "", max_chars: int = 1024) -> list[dict[str, Any]]:
    """Split on paragraph boundaries, merge small paragraphs up to max_chars."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks = []
    current = []
    current_len = 0
    for p in paras:
        if current_len + len(p) > max_chars and current:
            block = "\n\n".join(current)
            entities = extract_named_entities(block)
            chunks.append({
                "content": block,
                "source_url": source_url,
                "chunk_strategy": "context_aware",
                "named_entities": entities,
            })
            current = []
            current_len = 0
        current.append(p)
        current_len += len(p)
    if current:
        block = "\n\n".join(current)
        entities = extract_named_entities(block)
        chunks.append({
            "content": block,
            "source_url": source_url,
            "chunk_strategy": "context_aware",
            "named_entities": entities,
        })
    return chunks


def scrape_url(url: str) -> str:
    """Scrape text from URL (GraySentinel-style: BeautifulSoup)."""
    import requests
    from bs4 import BeautifulSoup
    try:
        from fake_useragent import UserAgent
        ua = UserAgent()
        headers = {"User-Agent": ua.random}
    except Exception:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; OSINT-Bot/1.0)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def get_embedder():
    """Lazy-load sentence-transformers model."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")


def run_pipeline(
    urls: list[str],
    strategies: list[str] | None = None,
) -> dict[str, Any]:
    """
    Full pipeline: scrape -> chunk -> NER -> embed -> store in Weaviate.
    strategies: ["chunk_by_title", "similarity_based", "context_aware"] or None for all.
    """
    strategies = strategies or ["chunk_by_title", "similarity_based", "context_aware"]
    all_chunks: list[dict[str, Any]] = []
    for url in urls:
        try:
            text = scrape_url(url)
        except Exception as e:
            continue
        for s in strategies:
            if s == "chunk_by_title":
                all_chunks.extend(chunk_by_title(text, url))
            elif s == "similarity_based":
                all_chunks.extend(chunk_similarity_based(text, url))
            elif s == "context_aware":
                all_chunks.extend(chunk_context_aware(text, url))

    if not all_chunks:
        return {"success": False, "error": "No chunks produced", "ingested": 0}

    try:
        model = get_embedder()
        texts = [c["content"] for c in all_chunks]
        vectors = model.encode(texts).tolist()
    except Exception as e:
        return {"success": False, "error": str(e), "ingested": 0}

    try:
        from backend.weaviate_client import _connect, ensure_schema, add_documents
        client = _connect()
        ensure_schema(client)
        add_documents(client, all_chunks, vectors)
        client.close()
    except Exception as e:
        return {"success": False, "error": str(e), "chunks": len(all_chunks), "ingested": 0}

    return {"success": True, "ingested": len(all_chunks), "urls": urls}
