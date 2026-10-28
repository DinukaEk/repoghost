from pathlib import Path
import pytest
from ghostcore.sample import create_demo_repo
from ghostcore.git_history import load_commits

@pytest.fixture(scope="function")
def demo(tmp_path):
    repo = create_demo_repo(tmp_path / "demo")
    _, commits = load_commits(repo, limit=30)
    return repo, commits
