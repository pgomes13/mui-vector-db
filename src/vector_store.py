"""
FAISS-backed vector store for MUI documentation chunks.

Persists both the FAISS index (binary) and the chunk metadata (JSON)
to the index/ directory so the store can be loaded without re-embedding.
"""

import json
from pathlib import Path
from dataclasses import asdict
from typing import Optional

import numpy as np
import faiss

from .chunker import Chunk

INDEX_FILE = "faiss.index"
META_FILE = "metadata.json"
DIM_FILE = "dim.txt"


class VectorStore:
    """
    Wraps a FAISS flat inner-product index (equivalent to cosine similarity
    when vectors are L2-normalised) with chunk metadata.
    """

    def __init__(self, dim: int):
        self.dim = dim
        # IndexFlatIP: exact search, cosine similarity (vecs must be unit norm)
        self._index: faiss.IndexFlatIP = faiss.IndexFlatIP(dim)
        self._chunks: list[Chunk] = []

    # ------------------------------------------------------------------
    # Building
    # ------------------------------------------------------------------

    def add(self, chunks: list[Chunk], embeddings: np.ndarray) -> None:
        """Add chunks and their pre-computed embeddings to the store."""
        if len(chunks) != embeddings.shape[0]:
            raise ValueError(
                f"Chunk count ({len(chunks)}) != embedding rows ({embeddings.shape[0]})"
            )
        vecs = embeddings.astype(np.float32)
        # Ensure unit norm (defensive — embedder already normalises)
        faiss.normalize_L2(vecs)
        self._index.add(vecs)
        self._chunks.extend(chunks)
        print(f"Index now holds {self._index.ntotal} vectors.")

    # ------------------------------------------------------------------
    # Searching
    # ------------------------------------------------------------------

    def search(
        self,
        query_vec: np.ndarray,
        top_k: int = 10,
        score_threshold: float = 0.0,
    ) -> list[tuple[Chunk, float]]:
        """
        Return up to top_k (chunk, score) pairs sorted by descending similarity.
        score is cosine similarity in [0, 1] (higher = more similar).
        """
        if self._index.ntotal == 0:
            return []

        q = query_vec.astype(np.float32).reshape(1, -1)
        faiss.normalize_L2(q)

        k = min(top_k, self._index.ntotal)
        scores, indices = self._index.search(q, k)

        results: list[tuple[Chunk, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            if score < score_threshold:
                continue
            results.append((self._chunks[idx], float(score)))

        return results

    def search_by_section(
        self,
        query_vec: np.ndarray,
        section: str,
        top_k: int = 10,
    ) -> list[tuple[Chunk, float]]:
        """Search but only return chunks from a specific section."""
        candidates = self.search(query_vec, top_k=top_k * 5)
        filtered = [(c, s) for c, s in candidates if c.section == section]
        return filtered[:top_k]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, index_dir: Path) -> None:
        index_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(index_dir / INDEX_FILE))
        with open(index_dir / META_FILE, "w") as f:
            json.dump([c.to_dict() for c in self._chunks], f)
        with open(index_dir / DIM_FILE, "w") as f:
            f.write(str(self.dim))
        print(
            f"Saved index ({self._index.ntotal} vectors, dim={self.dim}) "
            f"to {index_dir}"
        )

    @classmethod
    def load(cls, index_dir: Path) -> "VectorStore":
        index_path = index_dir / INDEX_FILE
        meta_path = index_dir / META_FILE
        dim_path = index_dir / DIM_FILE

        if not index_path.exists():
            raise FileNotFoundError(
                f"No FAISS index found at {index_path}. "
                "Run build_index.py first."
            )

        dim = int((dim_path).read_text().strip())
        store = cls(dim)
        store._index = faiss.read_index(str(index_path))

        with open(meta_path) as f:
            store._chunks = [Chunk.from_dict(d) for d in json.load(f)]

        print(
            f"Loaded index: {store._index.ntotal} vectors "
            f"(dim={dim}) from {index_dir}"
        )
        return store

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        section_counts: dict[str, int] = {}
        component_counts: dict[str, int] = {}
        for c in self._chunks:
            section_counts[c.section] = section_counts.get(c.section, 0) + 1
            if c.component_name:
                component_counts[c.component_name] = (
                    component_counts.get(c.component_name, 0) + 1
                )
        return {
            "total_vectors": self._index.ntotal,
            "dim": self.dim,
            "sections": section_counts,
            "top_components": sorted(
                component_counts.items(), key=lambda x: -x[1]
            )[:20],
        }

    def __len__(self) -> int:
        return self._index.ntotal
