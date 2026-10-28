# 👻 RepoGhost - Ask your repository what it remembers

**A local open-weight AI archaeologist for the code you thought was gone.**  
*Hacktoberfest 2026 · Open-Source AI Challenge · Week 4: Ghost in the Machine*

> “The code is gone from the working tree. Its story is still in Git.”

Every project has a ghost: an old bug fix nobody remembers, a retired feature that explains a design decision, or a deleted implementation somebody now needs to inspect. Git has the evidence, but finding it often requires guessing the exact file name or phrase used years ago.

RepoGhost makes that history searchable in natural language **without uploading the repository to an AI service**. It reads local commit messages, changed file names, and small diff excerpts; an open-weight embedding model matches questions with relevant historical commits. Each result provides its actual commit SHA and patch. For deleted files, a separate preview reads their earlier contents **without restoring or altering the working tree**.

## ✨ What it does

- **Ask the ghosts:** “Why did we stop storing authentication tokens?” or “How did we handle a network outage?” Receive ranked *actual commits*, not invented answers.
- **Visit the graveyard:** Browse deletion events and preview historical text using read-only Git commands.
- **Inspect evidence:** View commit dates, paths, original messages, and diff excerpts for verification.
- **Compare methods:** Switch between **open-weight semantic embeddings** and a deliberately simple keyword baseline.
- **Stay private:** Run inference on your machine. A model download is needed once; afterward, strict offline loading is available.
- **Try it safely:** Generate a **fictional 12-commit repository** with an old auth cache, retired inventory webhook, billing issue, outage, and more.

The theme is an analogy, not a claim of sentient code. RepoGhost doesn't impersonate developers, execute old code, or invent conversations with the past.

## 🧰 Stack

| Layer | Technology | Purpose |
|---|---|---|
| AI core | [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) | Open-weight semantic vectors (Apache 2.0 model) |
| Local inference | [Sentence Transformers](https://www.sbert.net/) | Download-once, offline-capable embedding inference |
| Repository history | Git CLI (read-only) | Commit metadata, text diff snippets, deleted-file previews |
| User interface | Streamlit | Dark, browser-based historical explorer |
| Tests | pytest | Pure-Python and temporary Git repo tests |
| CI | GitHub Actions | Tests on Python 3.11 using `python -m pytest -q` |

## 🚀 Quickstart on Windows

Prerequisites: **Git**, **Python 3.11** and an internet connection only for initial dependency/model download.

Open PowerShell in the extracted `repoghost-week4` directory:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python scripts/download_model.py
python -m streamlit run app.py
```

Open **http://localhost:8501**. Inside the application:

1. Click **Create fictional demo history** in the sidebar.
2. Click **Read the repository**.
3. In **Ask the ghosts**, enter `Why did we stop keeping login credentials in memory?` and use **Local AI embeddings**.
4. Expand a search result to see the original commit patch; do not assume it is correct without reading the evidence.
5. In **Lost files**, select `src/token_cache.py` to preview its contents from before deletion.
6. Switch to **Keyword baseline** to compare retrieval behavior.

You can scan an existing local Git repo by entering its path instead (e.g. `C:\Users\you\Documents\GitHub\remitmatch`). **Do not record or publish private repository history.**

### Strict offline test

After completing the initial model download, stop Streamlit with `Ctrl+C`, then:

```powershell
$env:REPOGHOST_OFFLINE="1"
python -m streamlit run app.py
```

Disconnect Wi-Fi and retry **Local AI embeddings**. The model is loaded from your local cache only. Offline behavior still needs to be verified on your machine before claiming it in a public submission.

### Test the code

```powershell
python -m pytest -q
python scripts/evaluate.py
```

Unit tests do not download the AI model: they use a stub embedder to test retrieval integration and focus on Git read-only behavior. `scripts/evaluate.py` **does** load the actual open-weight model and compares 6 predefined retrieval questions against a keyword-only baseline on a fictional repository. Report the measured numbers exactly as they appear; they are not a production benchmark.

## 🔍 Architecture

```text
A question
   |
   v
Local Git repository -- git log / diff-tree / show --> historical evidence
                                                     |
                                   commit messages + file names + diff lines
                                                     |
                                  open-weight sentence embedding model
                                                     |
                                         cosine similarity ranking
                                                     |
                               verified commit SHA + original diff excerpts
                                                     |
                           optional deleted-file preview from parent commit
```

The search index is computed on demand. We intentionally don't persist embeddings of sensitive repository contents. Similarity scores indicate closeness in vector space, **not factual probability**. Git history may include credentials or other secrets; local handling lowers external exposure but does not sanitize existing repositories.

## 🛡️ Safety design and current limits

- Git commands use `subprocess` with **no shell**. RepoGhost does not execute files or Git hooks, checkout commits, or write to your repository.
- Recovered content must correspond to a file truly deleted by the given SHA and must be a small **text file**. Binary and oversized history previews are rejected.
- The sample generator refuses to overwrite a nonempty demo folder.
- Patches are abbreviated and search is limited to the most recent 150 commits. Large, binary, renamed and merged histories need more advanced handling.
- Deleted-file events are historical events: files may have been re-added later. The app does not label them all as permanently missing.
- No cloud inference calls are made by the application. Installing packages and obtaining the model initially do involve internet access.
- This is a local prototype, **not a hardened multiuser service**. Run against repos you are authorized to inspect; do not expose Streamlit publicly to untrusted users.
- A matching commit may not provide the whole context of a decision. Check the original source and surrounding commits.

## 📂 Layout

```text
repoghost-week4/
├── app.py
├── ghostcore/
│   ├── git_history.py
│   ├── search.py
│   ├── model.py
│   └── sample.py
├── scripts/
│   ├── create_demo.py
│   ├── download_model.py
│   └── evaluate.py
├── tests/
├── .github/workflows/tests.yml
├── requirements.txt
├── requirements-dev.txt
├── DEV_SUBMISSION.md
└── DEMO_AND_PUBLISH.md
```

## License & credits

RepoGhost application code: **MIT License**. External model: **Apache 2.0** as stated on the model card; third-party dependency licenses apply separately. All sample repository entries are fictional. Not affiliated with GitHub, Git, Hugging Face or DEV.
