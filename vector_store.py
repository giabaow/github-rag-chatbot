import os
from pathlib import Path
from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# GPT4All embedding model — downloads ~45 MB on first run, then cached
EMBEDDING_MODEL = "all-MiniLM-L6-v2.gguf2.f16.gguf"

CHROMA_BASE_DIR = Path("data/vectors")


def _get_embeddings() -> GPT4AllEmbeddings:
    """Return a GPT4All embeddings instance (lazy model load)."""
    return GPT4AllEmbeddings(model_name=EMBEDDING_MODEL)


def build_vector_store(chunks: list[dict], collection_name: str) -> Chroma:
    """
    Embed all chunks and persist them into a ChromaDB collection.
    If a collection with the same name exists, it is replaced.

    Args:
        chunks: list of chunk dicts from chunker.py
        collection_name: unique name per repo (e.g. 'facebook-react')

    Returns:
        A LangChain Chroma vectorstore instance ready for similarity search.
    """
    persist_dir = str(CHROMA_BASE_DIR / collection_name)

    # Wipe existing collection so re-indexing the same repo is always fresh
    if Path(persist_dir).exists():
        import shutil
        shutil.rmtree(persist_dir)

    docs = [
        Document(page_content=chunk["text"], metadata=chunk["metadata"])
        for chunk in chunks
    ]

    embeddings = _get_embeddings()
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=persist_dir,
    )
    vectorstore.persist()
    print(f"Indexed {len(docs)} chunks into ChromaDB collection '{collection_name}'")
    return vectorstore


def load_vector_store(collection_name: str) -> Chroma:
    """
    Load an existing ChromaDB collection from disk.

    Raises FileNotFoundError if the collection has not been built yet.
    """
    persist_dir = str(CHROMA_BASE_DIR / collection_name)
    if not Path(persist_dir).exists():
        raise FileNotFoundError(
            f"No index found for '{collection_name}'. "
            "Please index the repository first."
        )

    embeddings = _get_embeddings()
    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=persist_dir,
    )


def similarity_search(
    query: str,
    vectorstore: Chroma,
    top_k: int = 5,
) -> list[tuple[Document, float]]:
    """
    Run a semantic similarity search against the vectorstore.

    Returns a list of (Document, relevance_score) tuples sorted by score desc.
    """
    results = vectorstore.similarity_search_with_relevance_scores(query, k=top_k)
    return results