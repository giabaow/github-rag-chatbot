"""
pipeline.py
LangChain RAG pipeline: retrieve relevant chunks from ChromaDB,
then pass them to Gemini 1.5 Flash to generate a grounded answer.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma

from backend.rag.repo_loader import clone_repo, extract_files, repo_name_from_url
from backend.rag.chunker import chunk_files
from backend.rag.vector_store import (
    build_vector_store,
    load_vector_store,
    similarity_search,
)

load_dotenv()

DATA_DIR = Path("data")

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

RAG_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are an expert code assistant. Your job is to answer questions
about a GitHub repository using ONLY the code context provided below.

Rules:
- Always cite the exact file path when referencing code (e.g. `src/auth.py`).
- If the answer cannot be found in the context, say so clearly.
- Be concise but complete. Use markdown for code blocks.

Code context:
{context}

Question: {question}

Answer:""",
)


def _build_llm() -> ChatGoogleGenerativeAI:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GOOGLE_API_KEY not set. Add it to your .env file."
        )
    return ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        google_api_key=api_key,
        temperature=0.2,
        convert_system_message_to_human=True,
    )


# ---------------------------------------------------------------------------
# Public pipeline functions
# ---------------------------------------------------------------------------

def index_repository(repo_url: str) -> dict:
    """
    Full indexing pipeline:
      1. Clone the repository
      2. Extract code files
      3. Chunk them
      4. Embed with GPT4All and store in ChromaDB

    Returns a summary dict.
    """
    collection = repo_name_from_url(repo_url)
    repo_path = DATA_DIR / "repos" / collection

    files = extract_files(clone_repo(repo_url, repo_path))
    if not files:
        raise ValueError("No supported code files found in this repository.")

    chunks = chunk_files(files)
    build_vector_store(chunks, collection)

    return {
        "collection": collection,
        "files_indexed": len(files),
        "chunks_created": len(chunks),
    }


def answer_question(repo_url: str, question: str, top_k: int = 5) -> dict:
    """
    RAG query pipeline:
      1. Load the ChromaDB collection for this repo
      2. Retrieve the top-k most relevant chunks
      3. Build a context string
      4. Ask Gemini 1.5 Flash to answer using that context

    Returns a dict with:
      - answer: the LLM's response (string)
      - sources: list of unique file paths cited
      - chunks: raw retrieved chunk texts (for display in UI)
    """
    collection = repo_name_from_url(repo_url)
    vectorstore = load_vector_store(collection)

    results: list[tuple[Document, float]] = similarity_search(
        question, vectorstore, top_k=top_k
    )

    if not results:
        return {
            "answer": "No relevant code was found for your question.",
            "sources": [],
            "chunks": [],
        }

    # Build context block
    context_parts = []
    for doc, score in results:
        context_parts.append(
            f"[Score: {score:.2f}] File: {doc.metadata.get('file_path', 'unknown')}\n"
            f"{doc.page_content}"
        )
    context = "\n\n---\n\n".join(context_parts)

    # Call Gemini via LangChain
    llm = _build_llm()
    prompt_text = RAG_PROMPT.format(context=context, question=question)
    response = llm.invoke(prompt_text)

    sources = list(
        dict.fromkeys(  # deduplicate while preserving order
            doc.metadata.get("file_path", "unknown") for doc, _ in results
        )
    )

    return {
        "answer": response.content,
        "sources": sources,
        "chunks": [
            {"text": doc.page_content, "score": round(score, 3), "path": doc.metadata.get("file_path")}
            for doc, score in results
        ],
    }


# import argparse

# if __name__ == "__main__":
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--url", required=True)
#     parser.add_argument("--question", required=True)
#     args = parser.parse_args()

#     # Index the repo
#     print(f"Indexing {args.url}...")
#     index_result = index_repository(args.url)
#     print(f"Indexed {index_result['files_indexed']} files, created {index_result['chunks_created']} chunks")

#     # Answer the question
#     print(f"\nAsking: {args.question}")
#     result = answer_question(args.url, args.question)

#     print(f"\nAnswer:\n{result['answer']}")
#     print(f"\nSources: {result['sources']}")