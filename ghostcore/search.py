"""Semantic retrieval with a transparent keyword-only comparison."""
from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
from math import sqrt
import re
from typing import Protocol, Sequence

from ghostcore.git_history import Commit


class Embedder(Protocol):
    def encode(self, texts: list[str], **kwargs: object) -> object: ...


@dataclass(frozen=True)
class Result:
    commit: Commit
    score: float
    method: str


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError("Embedding dimension mismatch")
    aa = sum(float(x) * float(x) for x in a)
    bb = sum(float(x) * float(x) for x in b)
    if aa == 0 or bb == 0:
        return 0.0
    return sum(float(x) * float(y) for x, y in zip(a, b)) / sqrt(aa * bb)


def semantic_search(query: str, commits: list[Commit], model: Embedder, top_k: int = 5) -> list[Result]:
    """Ranks historical evidence by actual local model embeddings, not canned responses."""
    if not query.strip() or not commits:
        return []
    if not 1 <= top_k <= 30:
        raise ValueError("top_k out of bounds")
    # Models implement encode; fake models in unit tests allow offline CI.
    vectors = model.encode([query.strip()] + [c.text for c in commits], normalize_embeddings=True)
    if len(vectors) != len(commits) + 1:
        raise ValueError("Model produced the wrong number of embeddings")
    output = [Result(c, cosine(vectors[0], vectors[i + 1]), "local AI") for i, c in enumerate(commits)]
    return sorted(output, key=lambda r: r.score, reverse=True)[:top_k]


STOPWORDS = frozenset("a an the i me my you it to from for in of on and or was were is are what how when why that did do with we this back by old".split())


def tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9_]+", text.lower()) if len(w) > 1 and w not in STOPWORDS]


def keyword_search(query: str, commits: list[Commit], top_k: int = 5) -> list[Result]:
    if not query.strip() or not commits:
        return []
    query_tokens = Counter(tokens(query))
    if not query_tokens:
        return []
    results = []
    for c in commits:
        content_tokens = Counter(tokens(c.text))
        score = sum(min(count, content_tokens.get(term, 0)) for term, count in query_tokens.items()) / sum(query_tokens.values())
        results.append(Result(c, score, "keyword baseline"))
    return sorted(results, key=lambda r: r.score, reverse=True)[:top_k]
