"""Read-only Git archaeology. Never checks out or executes repository code."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import os
import re
import subprocess

HASH_RE = re.compile(r"^[0-9a-f]{40,64}$")
MAX_SHOW_BYTES = 120_000


class HistoryError(RuntimeError):
    """A readable error for an inaccessible or invalid repository."""


def _git(repo: Path, *args: str, timeout: int = 12) -> bytes:
    """Execute Git without a shell; disable external diff and interactive prompts."""
    env = os.environ.copy()
    env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0", "GIT_CONFIG_NOSYSTEM": "1"})
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "--no-pager", *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
            env=env,
        )
    except FileNotFoundError as exc:
        raise HistoryError("Git is not installed or isn't available in PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise HistoryError("Git took too long to read the repository.") from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()[:320]
        raise HistoryError(detail or f"Git exited with code {result.returncode}")
    return result.stdout


def repository_root(folder: str | Path) -> Path:
    folder = Path(folder).expanduser().resolve()
    if not folder.is_dir():
        raise HistoryError(f"Folder not found: {folder}")
    root = _git(folder, "rev-parse", "--show-toplevel").decode("utf-8", "replace").strip()
    if not root:
        raise HistoryError("Not a Git repository.")
    return Path(root).resolve()


def _display(value: bytes) -> str:
    return value.decode("utf-8", "replace")


@dataclass(frozen=True)
class LostFile:
    path: str
    deletion_commit: str
    subject: str
    date: str


@dataclass(frozen=True)
class Commit:
    sha: str
    date: str
    subject: str
    body: str
    paths: tuple[str, ...]
    deleted: tuple[str, ...]
    diff_excerpt: str

    @property
    def text(self) -> str:
        # The embeddings are grounded in actual commit metadata and changed lines.
        return (
            f"Commit: {self.subject}\nDescription: {self.body}\n"
            f"Files: {' '.join(self.paths)}\nChanges: {self.diff_excerpt}"
        )[:6000]


def _changes(repo: Path, sha: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    raw = _git(repo, "diff-tree", "--root", "--no-commit-id", "--no-renames", "--name-status", "-r", "-z", sha)
    # With -z, --name-status format: STATUS\0PATH\0 for each change.
    entries = raw.split(b"\x00")
    paths: list[str] = []
    deleted: list[str] = []
    for pos in range(0, len(entries) - 1, 2):
        status = _display(entries[pos])
        path = _display(entries[pos + 1])
        if not status or not path:
            continue
        paths.append(path)
        if status.startswith("D"):
            deleted.append(path)
    return tuple(paths), tuple(deleted)


def _patch_excerpt(repo: Path, sha: str, max_chars: int = 3200) -> str:
    raw = _git(
        repo, "show", "--format=", "--no-ext-diff", "--no-textconv", "--no-renames",
        "--unified=0", "--no-color", sha,
    )
    # Avoid huge display, unbounded binary data, and excessive similarity to commit headers.
    lines = []
    for line in _display(raw[:MAX_SHOW_BYTES]).splitlines():
        if line.startswith(("+++ ", "--- ", "@@")):
            continue
        if line.startswith(("+", "-")) and len(line) <= 600:
            lines.append(line)
    return "\n".join(lines)[:max_chars]


def load_commits(folder: str | Path, limit: int = 60) -> tuple[Path, list[Commit]]:
    if not 1 <= limit <= 150:
        raise ValueError("Commit limit must be between 1 and 150")
    repo = repository_root(folder)
    raw = _git(repo, "log", "--no-show-signature", f"-n{limit}", "--date=short", "--format=%H%x1f%ad%x1f%s%x1f%b%x1e")
    commits: list[Commit] = []
    for record in raw.split(b"\x1e"):
        pieces = record.strip(b"\r\n").split(b"\x1f", 3)
        if len(pieces) != 4:
            continue
        sha, date, subject, body = (_display(p).strip() for p in pieces)
        if not HASH_RE.fullmatch(sha):
            continue
        paths, deleted = _changes(repo, sha)
        commits.append(Commit(sha, date, subject, body, paths, deleted, _patch_excerpt(repo, sha)))
    return repo, commits


def lost_file_events(commits: list[Commit]) -> list[LostFile]:
    return [
        LostFile(path, commit.sha, commit.subject, commit.date)
        for commit in commits for path in commit.deleted
    ]


def _safe_git_path(path: str) -> bool:
    # Git paths always use /, even on Windows. Disallow control chars and traversal.
    if not path or "\\" in path or "\x00" in path or any(ord(c) < 32 for c in path):
        return False
    pure = PurePosixPath(path)
    return not pure.is_absolute() and all(p not in ("..", ".") for p in path.split("/"))


def recover_deleted_content(folder: str | Path, deletion_sha: str, path: str, max_bytes: int = 100_000) -> str:
    """Preview historical text from first parent; never writes into the repository."""
    if not HASH_RE.fullmatch(deletion_sha):
        raise ValueError("Invalid commit ID")
    if not _safe_git_path(path):
        raise ValueError("Unsafe file path")
    repo = repository_root(folder)
    # Validate this really is a deletion recorded at that SHA, not an arbitrary file read.
    _, deleted = _changes(repo, deletion_sha)
    if path not in deleted:
        raise HistoryError("This file was not deleted by the selected commit.")
    raw = _git(repo, "show", f"{deletion_sha}^:{path}")
    if len(raw) > max_bytes:
        raise HistoryError("Historical file is too large to preview safely.")
    if b"\x00" in raw:
        raise HistoryError("Binary files are not available for text preview.")
    return raw.decode("utf-8", "replace")
