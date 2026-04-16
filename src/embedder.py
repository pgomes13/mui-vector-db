"""
Embedder using sentence-transformers.

Generates dense vector embeddings for text chunks and caches them
to disk so re-runs don't re-embed unchanged content.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Optional

import numpy as np
from tqdm import tqdm

# Lazy import — only load when needed to keep startup fast
_model = None

# Model chosen for a good balance of quality vs speed for semantic search.
# all-MiniLM-L6-v2 is fast (~14k docs/sec on CPU) and 384-dim.
DEFAULT_MODEL = "all-MiniLM-L6-v2"


def _get_model(model_name: str):
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print(f"Loading embedding model: {model_name}")
        _model = SentenceTransformer(model_name)
    return _model


def _text_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:16]


def embed_texts(
    texts: list[str],
    model_name: str = DEFAULT_MODEL,
    batch_size: int = 64,
    show_progress: bool = True,
) -> np.ndarray:
    """
    Embed a list of strings and return a float32 numpy array of shape (N, dim).
    """
    model = _get_model(model_name)
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=show_progress,
        convert_to_numpy=True,
        normalize_embeddings=True,   # cosine sim = dot product on unit vectors
    )
    return embeddings.astype(np.float32)


def embed_chunks(
    chunks: list,           # list[Chunk] — avoid circular import
    cache_path: Optional[Path] = None,
    model_name: str = DEFAULT_MODEL,
    batch_size: int = 64,
) -> np.ndarray:
    """
    Embed chunks, using an on-disk cache to avoid re-embedding unchanged text.

    Returns float32 ndarray of shape (len(chunks), embedding_dim).
    """
    texts = [c.text for c in chunks]

    if cache_path is not None and cache_path.exists():
        cached = np.load(str(cache_path))
        if cached.shape[0] == len(texts):
            print(f"Loaded {len(texts)} embeddings from cache: {cache_path}")
            return cached
        print(
            f"Cache size mismatch ({cached.shape[0]} vs {len(texts)}), "
            "re-embedding..."
        )

    print(f"Embedding {len(texts)} chunks with model '{model_name}'...")
    embeddings = embed_texts(texts, model_name=model_name, batch_size=batch_size)

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(str(cache_path), embeddings)
        print(f"Saved embeddings cache to {cache_path}")

    return embeddings


def embed_query(
    query: str,
    model_name: str = DEFAULT_MODEL,
) -> np.ndarray:
    """
    Embed a single query string. Returns float32 array of shape (dim,).
    """
    return embed_texts([query], model_name=model_name, show_progress=False)[0]


def embedding_dim(model_name: str = DEFAULT_MODEL) -> int:
    """Return the embedding dimension for a model (forces model load)."""
    return _get_model(model_name).get_sentence_embedding_dimension()
