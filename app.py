"""
app.py
Streamlit UI for the GitHub RAG Chatbot.
Run with: streamlit run app.py
"""

import sys
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from backend.rag.pipeline import index_repository, answer_question
from backend.rag.repo_loader import repo_name_from_url

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="GitHub RAG Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .source-badge {
        display: inline-block;
        background: #e8f4f8;
        color: #1a6580;
        border-radius: 4px;
        padding: 2px 8px;
        margin: 2px;
        font-size: 12px;
        font-family: monospace;
    }
    .chunk-expander { font-size: 13px; }
    .stChatMessage { border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "indexed_repo" not in st.session_state:
    st.session_state.indexed_repo = None

if "index_stats" not in st.session_state:
    st.session_state.index_stats = None

# ---------------------------------------------------------------------------
# Sidebar — repo input
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🤖 GitHub RAG Chatbot")
    st.caption("Chat with any public GitHub repository using AI")

    st.divider()

    st.subheader("1. Load a Repository")
    repo_url = st.text_input(
        "GitHub URL",
        placeholder="https://github.com/owner/repo",
        help="Must be a public repository.",
    )

    top_k = st.slider(
        "Retrieved chunks (top-k)",
        min_value=3,
        max_value=10,
        value=5,
        help="How many code snippets to retrieve per question. Higher = more context, slower.",
    )

    index_btn = st.button("🔍 Index Repository", use_container_width=True, type="primary")

    if index_btn:
        if not repo_url.startswith("https://github.com/"):
            st.error("Please enter a valid GitHub URL (https://github.com/...)")
        else:
            with st.spinner("Cloning & indexing… this takes 1–3 minutes for large repos."):
                try:
                    stats = index_repository(repo_url)
                    st.session_state.indexed_repo = repo_url
                    st.session_state.index_stats = stats
                    st.session_state.messages = []  # reset chat
                    st.success("Repository indexed!")
                except Exception as e:
                    st.error(f"Indexing failed: {e}")

    # Show index stats
    if st.session_state.index_stats:
        stats = st.session_state.index_stats
        st.divider()
        st.subheader("📊 Index stats")
        col1, col2 = st.columns(2)
        col1.metric("Files", stats["files_indexed"])
        col2.metric("Chunks", stats["chunks_created"])
        st.caption(f"Collection: `{stats['collection']}`")

    st.divider()

    st.subheader("Tech stack")
    st.markdown(
        """
        - **LLM** — Gemini 1.5 Flash  
        - **Embeddings** — GPT4All (local)  
        - **Vector DB** — ChromaDB  
        - **Orchestration** — LangChain  
        - **UI** — Streamlit  
        """
    )

    # Clear chat
    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ---------------------------------------------------------------------------
# Main area — chat
# ---------------------------------------------------------------------------
st.title("💬 Chat with your codebase")

if not st.session_state.indexed_repo:
    st.info(
        "👈 Paste a GitHub URL in the sidebar and click **Index Repository** to get started.",
        icon="ℹ️",
    )

    # Example repos
    st.subheader("Try these repos:")
    examples = [
        "https://github.com/tiangolo/fastapi",
        "https://github.com/streamlit/streamlit",
        "https://github.com/pallets/flask",
    ]
    for ex in examples:
        st.code(ex, language=None)

else:
    st.caption(
        f"Chatting with: **{st.session_state.indexed_repo}**  •  "
        f"Top-k: {top_k} chunks"
    )

    # Render chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            # Show sources for assistant messages
            if msg["role"] == "assistant" and msg.get("sources"):
                st.markdown("**Sources:**")
                badges = "".join(
                    f'<span class="source-badge">📄 {s}</span>'
                    for s in msg["sources"]
                )
                st.markdown(badges, unsafe_allow_html=True)

            # Show retrieved chunks in expander
            if msg["role"] == "assistant" and msg.get("chunks"):
                with st.expander(f"View {len(msg['chunks'])} retrieved code chunks"):
                    for i, chunk in enumerate(msg["chunks"]):
                        st.markdown(
                            f"**Chunk {i+1}** — `{chunk['path']}` "
                            f"(relevance: {chunk['score']})"
                        )
                        # Detect language from extension for syntax highlighting
                        ext = Path(chunk["path"]).suffix.lstrip(".")
                        lang = ext if ext in {"py","js","ts","tsx","jsx","go","rs","java","md"} else "text"
                        st.code(chunk["text"], language=lang)
                        st.divider()

    # Chat input
    if question := st.chat_input("Ask anything about this repository…"):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        # Generate answer
        with st.chat_message("assistant"):
            with st.spinner("Searching codebase and generating answer…"):
                try:
                    result = answer_question(
                        st.session_state.indexed_repo,
                        question,
                        top_k=top_k,
                    )
                    answer = result["answer"]
                    sources = result["sources"]
                    chunks = result["chunks"]

                    st.markdown(answer)

                    if sources:
                        st.markdown("**Sources:**")
                        badges = "".join(
                            f'<span class="source-badge">📄 {s}</span>'
                            for s in sources
                        )
                        st.markdown(badges, unsafe_allow_html=True)

                    with st.expander(f"View {len(chunks)} retrieved code chunks"):
                        for i, chunk in enumerate(chunks):
                            st.markdown(
                                f"**Chunk {i+1}** — `{chunk['path']}` "
                                f"(relevance: {chunk['score']})"
                            )
                            ext = Path(chunk["path"]).suffix.lstrip(".")
                            lang = ext if ext in {"py","js","ts","tsx","jsx","go","rs","java","md"} else "text"
                            st.code(chunk["text"], language=lang)
                            st.divider()

                except FileNotFoundError:
                    answer = "⚠️ This repository has not been indexed yet. Please index it first."
                    sources, chunks = [], []
                    st.warning(answer)

                except Exception as e:
                    answer = f"⚠️ Error generating answer: {e}"
                    sources, chunks = [], []
                    st.error(answer)

        # Save to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "chunks": chunks,
        })