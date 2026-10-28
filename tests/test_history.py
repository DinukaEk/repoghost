import pytest
from ghostcore.git_history import (
    Commit, HistoryError, _safe_git_path, _changes, load_commits, lost_file_events,
    recover_deleted_content, repository_root,
)
from ghostcore.sample import create_demo_repo


def test_creates_twelve_commits(demo):
    _, commits = demo
    assert len(commits) == 12


def test_commits_newest_first(demo):
    _, commits = demo
    assert commits[0].subject.startswith("Document incident")
    assert commits[-1].subject.startswith("Start LanternLedger")


def test_commits_have_date_hash_and_text(demo):
    _, commits = demo
    for c in commits:
        assert len(c.sha) == 40
        assert c.date.startswith("2025-05-")
        assert c.subject in c.text


def test_history_contains_deleted_files(demo):
    _, commits = demo
    lost = lost_file_events(commits)
    assert {x.path for x in lost} == {"src/token_cache.py", "src/legacy_webhook.py"}


def test_read_deleted_token_cache(demo):
    repo, commits = demo
    event = next(x for x in lost_file_events(commits) if x.path.endswith("token_cache.py"))
    text = recover_deleted_content(repo, event.deletion_commit, event.path)
    assert "SESSION_TTL = 600" in text


def test_read_deleted_webhook(demo):
    repo, commits = demo
    event = next(x for x in lost_file_events(commits) if x.path.endswith("legacy_webhook.py"))
    text = recover_deleted_content(repo, event.deletion_commit, event.path)
    assert "parse_legacy_inventory" in text


def test_recovers_without_restoring_file(demo):
    repo, commits = demo
    event = next(x for x in lost_file_events(commits) if x.path.endswith("token_cache.py"))
    recover_deleted_content(repo, event.deletion_commit, event.path)
    assert not (repo / event.path).exists()


def test_unsafe_paths():
    for p in ["", "/etc/passwd", "../passwd", "a/../secrets", "./file", "a\\..\\b", "nul\x00byte", "a\nname"]:
        assert not _safe_git_path(p)
    assert _safe_git_path("src/token_cache.py")
    assert _safe_git_path("folder/my file.txt")


def test_bad_commit_hash_rejected(demo):
    repo, _ = demo
    with pytest.raises(ValueError):
        recover_deleted_content(repo, "HEAD; rm -rf .", "src/token_cache.py")


def test_safe_hash_cannot_read_arbitrary_file(demo):
    repo, commits = demo
    with pytest.raises(HistoryError, match="not deleted"):
        recover_deleted_content(repo, commits[0].sha, "README.md")


def test_path_traversal_rejected(demo):
    repo, commits = demo
    with pytest.raises(ValueError):
        recover_deleted_content(repo, commits[0].sha, "../secrets")


def test_binary_preview_rejected(demo):
    repo, commits = demo
    event = next(x for x in lost_file_events(commits) if x.path.endswith("token_cache.py"))
    with pytest.raises(HistoryError, match="too large"):
        recover_deleted_content(repo, event.deletion_commit, event.path, max_bytes=1)


def test_invalid_repo(tmp_path):
    with pytest.raises(HistoryError):
        repository_root(tmp_path)


def test_subfolder_resolves_to_root(demo):
    repo, _ = demo
    assert repository_root(repo / "src") == repo


def test_invalid_commit_limit(demo):
    repo, _ = demo
    with pytest.raises(ValueError):
        load_commits(repo, 151)
    with pytest.raises(ValueError):
        load_commits(repo, 0)


def test_limited_history(demo):
    repo, _ = demo
    _, limited = load_commits(repo, 2)
    assert len(limited) == 2


def test_no_existing_folder_overwrite(demo):
    repo, commits = demo
    with pytest.raises(FileExistsError):
        create_demo_repo(repo)
    assert len(commits) == 12


def test_no_extra_files_created_on_read(demo):
    repo, commits = demo
    before = {p.relative_to(repo) for p in repo.rglob('*') if '.git' not in p.parts}
    load_commits(repo)
    after = {p.relative_to(repo) for p in repo.rglob('*') if '.git' not in p.parts}
    assert before == after


def test_root_commit_paths_detected(demo):
    repo, commits = demo
    first = commits[-1]
    assert "README.md" in first.paths
    assert "src/app.py" in first.paths


def test_diff_has_real_changes(demo):
    _, commits = demo
    c = next(c for c in commits if "rounding" in c.subject)
    assert "ROUND_HALF_UP" in c.diff_excerpt
