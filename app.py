"""RepoGhost — local AI archaeology for Git repositories.

Run: python -m streamlit run app.py
"""
from pathlib import Path
import os

import streamlit as st

from ghostcore.git_history import (
    HistoryError, load_commits, lost_file_events, recover_deleted_content,
    repository_root,
)
from ghostcore.model import MODEL_ID, load_model
from ghostcore.sample import create_demo_repo
from ghostcore.search import keyword_search, semantic_search

ROOT = Path(__file__).resolve().parent
DEMO = ROOT / "demo_repository"

st.set_page_config(page_title="RepoGhost | Git history, resurrected", page_icon="👻", layout="wide")
st.markdown("""
<style>
.stApp {background: radial-gradient(circle at 88% 0%, #201835 0, #0d1119 37%, #0b0e14 100%); color: #e7e8f0;}
[data-testid="stSidebar"] {background: #101522;}
[data-testid="stMetric"] {background:#151b29;border:1px solid #303149;border-radius:14px;padding:14px 20px;}
[data-testid="stMetricValue"] {color:#bba4ff;}
.hero {padding:28px 30px;background:linear-gradient(125deg,#251a3c,#151d32);border:1px solid #594778;border-radius:22px;margin-bottom:20px;}
.hero h1 {color:#f0eaff;font-size:2.45rem;margin:0 0 6px;font-weight:790;letter-spacing:-0.06rem;}
.hero p {color:#c5bfd7;font-size:1rem;margin:0;max-width:800px;}
.eyebrow {text-transform:uppercase;color:#c6a7ff;font-size:0.8rem;letter-spacing:0.12rem;font-weight:650;}
.ghostnote {border-left:3px solid #a78bfa;padding:8px 15px;background:rgba(154,113,250,.1);border-radius:0 8px 8px 0;margin:12px 0;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero"><div class="eyebrow">⟡ HACKTOBERFEST 2026 · GHOST IN THE MACHINE</div>
<h1>👻 RepoGhost</h1>
<p>Every codebase has ghosts. Ask what happened, uncover deleted files, and listen to your project's actual Git history — using open-weight AI on your laptop.</p></div>
""", unsafe_allow_html=True)

@st.cache_resource(show_spinner="Awakening the local embedding model…")
def cached_model(offline: bool):
    return load_model(offline=offline)


with st.sidebar:
    st.markdown("### 🕯️ The Crypt")
    st.caption("RepoGhost reads local commits only. It never checks out, restores or edits repository files.")
    repo_input = st.text_input("Path to an existing Git repository", value=st.session_state.get("repo_path", str(DEMO)))
    if st.button("✨ Create fictional demo history", use_container_width=True):
        try:
            if DEMO.exists() and (DEMO / ".git").is_dir():
                st.info("The demo is already here. Keeping existing data unchanged.")
            else:
                create_demo_repo(DEMO)
                st.success("12 fictional commits created.")
            st.session_state.repo_path = str(DEMO)
            st.rerun()
        except (FileExistsError, HistoryError, OSError) as error:
            st.error(str(error))
    count = st.slider("Maximum commits to scan", min_value=10, max_value=100, value=40, step=10)
    offline = st.checkbox("Strict offline model loading", value=os.environ.get("REPOGHOST_OFFLINE") == "1", help="After downloading model once, this prevents any network model retrieval.")
    if st.button("🔎 Read the repository", type="primary", use_container_width=True):
        try:
            repo, commits = load_commits(repo_input, limit=count)
            st.session_state.repo_path = str(repo)
            st.session_state.commits = commits
            st.session_state.repo = str(repo)
            st.session_state.pop("results", None)
            st.session_state.pop("query", None)
            st.success(f"Read {len(commits)} historical commits.")
        except (HistoryError, ValueError, OSError) as error:
            st.error(str(error))
    st.markdown("---")
    st.caption(f"Embedding model: `{MODEL_ID}`")
    st.caption("No cloud AI API • No generated facts • Read-only access")

commits = st.session_state.get("commits", [])
repo = st.session_state.get("repo")
if not commits:
    st.info("**Start here:** click **Create fictional demo history**, then **Read the repository**. Or enter the path of one of your own Git projects.")
    st.markdown("""<div class="ghostnote">"The commit was deleted, but its story wasn't."<br>RepoGhost uses semantic embeddings to discover meaning in actual commit messages, file paths, and patches.</div>""", unsafe_allow_html=True)
    st.stop()

lost = lost_file_events(commits)
col1, col2, col3 = st.columns(3)
col1.metric("History entries", len(commits))
col2.metric("Deletion events", len(lost))
col3.metric("Files touched", len({path for c in commits for path in c.paths}))
st.caption(f"Reading **{repo}** · Only your most recent {len(commits)} commits are indexed. Commit evidence is not automatically proof of why a developer made a change.")

search_tab, deleted_tab, timeline_tab, about_tab = st.tabs(["🔮 Ask the ghosts", "🪦 Lost files", "🕰️ The timeline", "🔒 Under the hood"])
with search_tab:
    st.subheader("Ask a question about what your codebase remembers")
    st.caption("Example: Why did we remove the old token cache? · Where did we handle network failures? · What happened to the inventory webhook?")
    with st.form("ghost_search"):
        query = st.text_input("Your question", value=st.session_state.get("query", ""), placeholder="What happened to that old authentication cache?")
        method = st.radio("Retrieval method", ["Local AI embeddings", "Keyword baseline"], horizontal=True)
        top_n = st.slider("Results", 1, 8, 4)
        submitted = st.form_submit_button("👻 Summon the evidence", type="primary")
    if submitted:
        st.session_state.query = query
        if not query.strip():
            st.warning("Enter a question first.")
        else:
            try:
                if method == "Local AI embeddings":
                    model = cached_model(offline)
                    result = semantic_search(query, commits, model, top_k=top_n)
                else:
                    result = keyword_search(query, commits, top_k=top_n)
                st.session_state.results = result
                st.session_state.search_method = method
            except Exception as exc:
                st.error(f"AI model unavailable: {exc}")
                st.info("Install requirements and run `python scripts/download_model.py` first. You may inspect the keyword baseline while setting it up.")
                st.session_state.pop("results", None)
    results = st.session_state.get("results", [])
    if results:
        st.caption(f"Search method: **{st.session_state.get('search_method', 'Unknown')}**. A similarity score is a ranking signal, not probability or factual confidence.")
        for i, hit in enumerate(results, 1):
            c = hit.commit
            with st.container(border=True):
                st.markdown(f"**{i}. {c.subject}**")
                st.caption(f"{c.date} · `{c.sha[:10]}` · Similarity/overlap: `{hit.score:.3f}` · {hit.method}")
                if c.paths:
                    st.write("**Changed files:** " + ", ".join(f"`{p}`" for p in c.paths[:12]))
                if c.body:
                    st.write("**Developer's original notes:**", c.body)
                with st.expander("🔎 View the original diff evidence"):
                    st.code(c.diff_excerpt or "No text patch available for this commit.", language="diff")
    elif submitted and query.strip():
        st.info("No results in the selected commit range.")

with deleted_tab:
    st.subheader("Recover knowledge, not your working tree")
    st.write("These files were deleted at the listed commits. RepoGhost previews their previous contents directly from Git objects and only downloads a copy when you request it.")
    if not lost:
        st.info("No file deletions found in the scanned commits. Scan more history to look further back.")
    else:
        options = {f"{event.date} · {event.path} · {event.deletion_commit[:8]}": event for event in lost}
        key = st.selectbox("Select a deletion event", list(options))
        selected = options[key]
        st.caption(f"Removed by: **{selected.subject}** · `{selected.deletion_commit[:12]}`")
        try:
            old_text = recover_deleted_content(repo, selected.deletion_commit, selected.path)
            st.code(old_text, language=None, line_numbers=True)
            st.download_button("📜 Download historical text copy", data=old_text.encode("utf-8"), file_name=Path(selected.path).name, mime="text/plain", help="Saves a copy in your browser's download folder. It does not restore or change the Git repository.")
        except (HistoryError, ValueError, OSError) as exc:
            st.warning(f"Cannot preview this historical file: {exc}")

with timeline_tab:
    st.subheader("A timeline of real commits")
    for c in commits:
        with st.expander(f"{c.date}  ·  {c.subject}  ·  {c.sha[:8]}"):
            st.caption(f"Files: {', '.join(c.paths) if c.paths else 'None'}")
            if c.deleted:
                st.warning("Deleted in this commit: " + ", ".join(c.deleted))
            if c.body:
                st.write(c.body)
            st.code(c.diff_excerpt or "No text diff", language="diff")

with about_tab:
    st.markdown("""
    #### How the ghost actually works
    1. Git reads existing commit messages, dates, file changes and small text diffs **locally**.
    2. An **open-weight Sentence Transformers MiniLM** model turns your question and each commit's historical evidence into numeric vectors.
    3. Cosine similarity ranks relevant commits. The app shows SHA IDs and original patches, not generated stories.
    4. Deleted-file previews use `git show` to read earlier versions without checking out files or executing code.

    **Why not a cloud chatbot?** Repository history can contain confidential code, incidents or old secrets. Local processing keeps these inputs off third-party AI endpoints.

    **Limits:** Embeddings can retrieve the wrong commit; no calibrated reliability score is provided. Scan is capped, patches are truncated, binary files aren't previewed, and the app is intended for a trusted local machine. Never share confidential Git output in a public recording.
    """)
