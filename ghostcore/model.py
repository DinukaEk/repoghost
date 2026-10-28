"""Local open-weight embeddings: no network service or paid API calls."""
from __future__ import annotations
import os

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"


def load_model(offline: bool | None = None):
    from sentence_transformers import SentenceTransformer
    if offline is None:
        offline = os.environ.get("REPOGHOST_OFFLINE", "0").strip().lower() in ("1", "true", "yes")
    # local_files_only makes offline test reproducible; no silent online fallback.
    return SentenceTransformer(MODEL_ID, local_files_only=offline, trust_remote_code=False)
