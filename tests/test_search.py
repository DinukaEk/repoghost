import pytest
from ghostcore.git_history import Commit
from ghostcore.search import cosine, tokens, keyword_search, semantic_search


def C(subject, body=""):
    return Commit("a" * 40, "2025-05-01", subject, body, tuple(), tuple(), body)

class StubModel:
    def encode(self, texts, **kwargs):
        vectors = []
        for text in texts:
            lower = text.lower()
            vectors.append([1.0 if "cache" in lower else 0.0,
                            1.0 if "network" in lower else 0.0,
                            1.0 if "currency" in lower else 0.0])
        return vectors

class BrokenModel:
    def encode(self, texts, **kwargs):
        return [[1.0]]


def test_cosine_identical():
    assert cosine([1, 2], [1, 2]) == pytest.approx(1)


def test_cosine_orthogonal():
    assert cosine([1, 0], [0, 1]) == 0


def test_zero_norm():
    assert cosine([0, 0], [1, 1]) == 0


def test_dimension_error():
    with pytest.raises(ValueError):
        cosine([1], [1, 2])


def test_keyword_basic():
    commits = [C("Fix currency rounding"), C("Fix network error")]
    assert keyword_search("currency rounding", commits)[0].commit.subject == "Fix currency rounding"


def test_keyword_empty():
    assert keyword_search("", [C("foo")]) == []
    assert keyword_search("the and", [C("foo")]) == []


def test_keyword_top_k():
    assert len(keyword_search("currency", [C("currency") for _ in range(6)], top_k=2)) == 2


def test_semantic_ranking_with_stub():
    commits = [C("Network error"), C("Old cache removed"), C("Currency fix")]
    got = semantic_search("cache", commits, StubModel(), 2)
    assert got[0].commit.subject == "Old cache removed"
    assert len(got) == 2


def test_semantic_query_empty():
    assert semantic_search(" ", [C("cache")], StubModel()) == []


def test_semantic_invalid_k():
    with pytest.raises(ValueError):
        semantic_search("cache", [C("cache")], StubModel(), 0)


def test_semantic_bad_encoder():
    with pytest.raises(ValueError, match="wrong number"):
        semantic_search("cache", [C("cache")], BrokenModel())


def test_tokens_remove_stopwords():
    assert "the" not in tokens("The old currency import")
    assert "currency" in tokens("The old currency import")


def test_deterministic_keyword_ties():
    commits = [C("Apple"), C("Banana")]
    assert keyword_search("orange", commits)[0].commit.subject == "Apple"


def test_true_semantic_embeddings_use_all_commits():
    seen = []
    class CheckModel:
        def encode(self, texts, **kwargs):
            seen.extend(texts)
            return [[1.0, 0.0] for _ in texts]
    commits = [C("a"), C("b"), C("c")]
    semantic_search("anything", commits, CheckModel())
    assert len(seen) == 4
