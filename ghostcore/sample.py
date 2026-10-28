"""A fully fictional, deterministic miniature software history for safe demonstrations."""
from __future__ import annotations
from pathlib import Path
import os
import subprocess

from ghostcore.git_history import HistoryError


def _run(folder: Path, *args: str, day: int = 0) -> None:
    env = os.environ.copy()
    stamp = f"2025-05-{1 + day:02d}T12:00:00+00:00"
    env.update({"GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp, "GIT_TERMINAL_PROMPT": "0"})
    res = subprocess.run(["git", "-C", str(folder), *args], env=env, capture_output=True, text=True)
    if res.returncode:
        raise HistoryError(f"Demo Git command failed: {res.stderr.strip()[:240]}")


def create_demo_repo(target: str | Path) -> Path:
    folder = Path(target).expanduser().resolve()
    if folder.exists() and any(folder.iterdir()):
        raise FileExistsError("Demo folder already contains files; refusing to overwrite anything.")
    folder.mkdir(parents=True, exist_ok=True)
    _run(folder, "init", "-q", "-b", "main")
    _run(folder, "config", "user.name", "RepoGhost Demo")
    _run(folder, "config", "user.email", "demo@example.invalid")
    files: dict[str, str | None] = {}

    def commit(subject: str, changes: dict[str, str | None], day: int) -> None:
        for name, contents in changes.items():
            path = folder / name
            if contents is None:
                if path.exists():
                    path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(contents, encoding="utf-8")
        _run(folder, "add", "-A", day=day)
        _run(folder, "commit", "-q", "-m", subject, day=day)

    commit("Start LanternLedger: an invoice tool for the midnight shift", {
        "README.md": "# LanternLedger\nA tiny fictional billing tool built for RepoGhost demos.\n",
        "src/app.py": "def welcome():\n    return 'Welcome to LanternLedger'\n",
    }, 0)
    commit("Batch invoices for small merchants", {
        "src/invoices.py": "def batch_invoices(rows):\n    return [row for row in rows if row.get('amount', 0) > 0]\n",
        "docs/billing.md": "Group billing rows into one invoice run at the end of the day.\n",
    }, 1)
    commit("Keep a retry queue when deliveries fail", {
        "src/queue.py": "def pending_deliveries(events):\n    # Retain messages lost to temporary network failure\n    return [e for e in events if not e.get('delivered')]\n",
    }, 2)
    commit("Add short-lived sign-in token cache to speed requests", {
        "src/token_cache.py": "# Historical teaching sample; do not reuse in production.\nSESSION_TTL = 900\ndef should_refresh(age):\n    return age >= SESSION_TTL\n",
    }, 3)
    commit("Correct expiration check on cached sessions", {
        "src/token_cache.py": "# Historical teaching sample; do not reuse in production.\nSESSION_TTL = 600\ndef should_refresh(age):\n    # Refresh before the session expires\n    return age >= SESSION_TTL - 60\n",
    }, 4)
    commit("Retire token cache after authentication security review", {
        "src/token_cache.py": None,
        "docs/auth.md": "The old sign-in cache was removed after a security review.\nUse direct session verification instead of storing authentication token snapshots.\n",
    }, 5)
    commit("Create webhook listener for legacy inventory integrations", {
        "src/legacy_webhook.py": "def parse_legacy_inventory(event):\n    return event.get('sku'), event.get('qty')\n",
    }, 6)
    commit("Remove outdated inventory webhook integration", {
        "src/legacy_webhook.py": None,
        "docs/integrations.md": "Legacy warehouse callbacks are sunset. Modern inventory imports use scheduled polling.\n",
    }, 7)
    commit("Fix currency rounding discrepancy in invoice totals", {
        "src/invoices.py": "from decimal import Decimal, ROUND_HALF_UP\ndef invoice_total(amounts):\n    total = sum(Decimal(str(a)) for a in amounts)\n    return total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)\n",
    }, 8)
    commit("Migrate CSV ingestion to validated import pipeline", {
        "src/imports.py": "def validate_import(headers):\n    required = {'customer', 'amount', 'date'}\n    return required.issubset(set(headers))\n",
        "docs/imports.md": "Reject malformed spreadsheet rows before creating accounting entries.\n",
    }, 9)
    commit("Revert abandoned dark dashboard experiment", {
        "src/dashboard_theme.py": "def active_theme():\n    return 'classic'  # Removed experimental theme flag\n",
    }, 10)
    commit("Document incident: delayed jobs after a network outage", {
        "docs/incident.md": "Postmortem: outbound notifications piled up during an intermittent network outage.\nThe retry queue now waits for service recovery before replaying pending jobs.\n",
    }, 11)
    return folder
