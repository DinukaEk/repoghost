"""Optional real-model comparison; use only after installing model dependencies."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tempfile import TemporaryDirectory
from ghostcore.git_history import load_commits
from ghostcore.model import load_model
from ghostcore.sample import create_demo_repo
from ghostcore.search import semantic_search, keyword_search

CASES = [
    ("How did we deal with messages missing because the server connection dropped?", "Keep a retry queue"),
    ("Why did we stop keeping login credentials in memory?", "Retire token cache"),
    ("Can I find the ancient callback handler for warehouse stock events?", "Remove outdated inventory webhook"),
    ("Where was the decimal precision mismatch in customer billing resolved?", "Fix currency rounding"),
    ("What happened when notification delivery slowed during a service interruption?", "Document incident"),
    ("Where did we switch away from spreadsheets for loading accounting entries?", "Migrate CSV ingestion"),
]


def score(results, expected):
    return bool(results and expected.lower() in results[0].commit.subject.lower())


if __name__ == "__main__":
    print("Loading local open-weight model…")
    model = load_model()
    with TemporaryDirectory(prefix="repoghost-evaluation-") as tmp:
        _, commits = load_commits(create_demo_repo(Path(tmp) / "demo"))
        a = b = 0
        for query, expected in CASES:
            ai = semantic_search(query, commits, model, top_k=1)
            baseline = keyword_search(query, commits, top_k=1)
            a += score(ai, expected)
            b += score(baseline, expected)
            print(f"\nQuery: {query}\n  AI: {ai[0].commit.subject if ai else 'none'}\n  keyword: {baseline[0].commit.subject if baseline else 'none'}\n  expected: {expected}")
        print(f"\nSynthetic top-1 retrieval — embeddings: {a}/{len(CASES)}")
        print(f"Synthetic top-1 retrieval — keyword baseline: {b}/{len(CASES)}")
        print("Small fictional dataset, not a production benchmark. Search scores are not calibrated confidence.")
