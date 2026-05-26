"""
Username permutation generator for OSINT enumeration.
Keyless — produces candidate usernames from a seed name or handle.
"""
from __future__ import annotations

import re
from typing import Any

_SEPARATORS = (".", "_", "-", "")
_COMMON_SUFFIXES = ("", "1", "01", "123", "official", "real", "x", "tv", "dev")


def _tokens(seed: str) -> list[str]:
    s = seed.strip().lower()
    s = re.sub(r"[^a-z0-9.\-_@ ]", "", s)
    if "@" in s:
        s = s.split("@", 1)[0]
    parts = re.split(r"[\s.\-_]+", s)
    return [p for p in parts if p and len(p) >= 2]


def _permutations_from_parts(parts: list[str], max_results: int) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    def add(u: str) -> None:
        u = u.strip().lower()
        if not u or len(u) < 2 or u in seen:
            return
        seen.add(u)
        out.append(u)

    if not parts:
        return out

    if len(parts) == 1:
        base = parts[0]
        add(base)
        for suf in _COMMON_SUFFIXES:
            add(base + suf)
        return out[:max_results]

    first, last = parts[0], parts[-1]
    fi, li = first[0], last[0]

    patterns = [
        first,
        last,
        first + last,
        last + first,
        f"{first}{last}",
        f"{last}{first}",
        f"{fi}{last}",
        f"{first}{li}",
        f"{fi}{li}",
        f"{last}{first}",
    ]
    for sep in _SEPARATORS:
        patterns.extend(
            [
                f"{first}{sep}{last}",
                f"{last}{sep}{first}",
                f"{fi}{sep}{last}",
                f"{first}{sep}{li}",
            ]
        )

    for p in patterns:
        add(p)
        for suf in _COMMON_SUFFIXES[:4]:
            add(p + suf)
        if len(out) >= max_results:
            break

    return out[:max_results]


def username_permutate(seed: str, max_results: int = 50) -> dict[str, Any]:
    """
    Generate username candidates from a full name, email local-part, or handle.
    """
    seed = (seed or "").strip()
    if not seed:
        return {"success": False, "error": "Seed is required", "seed": seed}

    parts = _tokens(seed)
    permutations = _permutations_from_parts(parts, max_results=max(1, min(max_results, 200)))

    return {
        "success": True,
        "seed": seed,
        "tokens": parts,
        "count": len(permutations),
        "permutations": permutations,
    }
