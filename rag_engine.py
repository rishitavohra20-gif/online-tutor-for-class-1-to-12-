"""
rag_engine.py - RAG pipeline: chunk documents, embed them, store in ChromaDB
with class + subject as metadata so retrieval can be filtered per student selection.

This is what lets ONE tutor system serve Class 1-12 x every subject, instead of
building a separate system for each combination.
"""

import os
import chromadb
from chromadb.utils import embedding_functions
from pypdf import PdfReader

CHROMA_DIR = "chroma_store"


def get_chroma_client():
    return chromadb.PersistentClient(path=CHROMA_DIR)


def get_collection():
    """
    Uses ChromaDB's built-in free local embedding model (all-MiniLM-L6-v2).
    Runs on your own machine, no API key or cost involved.
    """
    client = get_chroma_client()
    embed_fn = embedding_functions.DefaultEmbeddingFunction()
    return client.get_or_create_collection(
        name="tutor_content",
        embedding_function=embed_fn
    )


def chunk_text(text, chunk_size=800, overlap=100):
    """Simple sliding-window chunking by characters."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return [c.strip() for c in chunks if c.strip()]


def ingest_pdf(file_path, class_level, subject, topic):
    """Reads a PDF, chunks it, and stores embeddings tagged with class/subject/topic."""
    reader = PdfReader(file_path)
    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"

    chunks = chunk_text(full_text)
    collection = get_collection()

    ids = [f"{class_level}_{subject}_{topic}_{i}" for i in range(len(chunks))]
    metadatas = [
        {"class_level": class_level, "subject": subject, "topic": topic}
        for _ in chunks
    ]

    if chunks:
        collection.add(documents=chunks, ids=ids, metadatas=metadatas)

    return len(chunks)


def ingest_raw_text(text, class_level, subject, topic):
    """Same as ingest_pdf but for plain text/notes pasted directly."""
    chunks = chunk_text(text)
    collection = get_collection()

    ids = [f"{class_level}_{subject}_{topic}_{i}" for i in range(len(chunks))]
    metadatas = [
        {"class_level": class_level, "subject": subject, "topic": topic}
        for _ in chunks
    ]

    if chunks:
        collection.add(documents=chunks, ids=ids, metadatas=metadatas)

    return len(chunks)


def retrieve_context(query, class_level, subject, n_results=4):
    """Retrieves the most relevant chunks, filtered to the student's class + subject."""
    collection = get_collection()

    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where={
                "$and": [
                    {"class_level": {"$eq": class_level}},
                    {"subject": {"$eq": subject}}
                ]
            }
        )
        docs = results.get("documents", [[]])[0]
        return docs
    except Exception:
        return []
