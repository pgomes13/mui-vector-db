"""
High-level search interface for the MUI vector database.

Provides semantic search with optional post-filters and result deduplication.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .chunker import Chunk
from .embedder import embed_query, DEFAULT_MODEL
from .vector_store import VectorStore


@dataclass
class SearchResult:
    rank: int
    score: float
    chunk_id: str
    url: str
    title: str
    component_name: str
    section: str
    is_code: bool
    text: str
    headings_context: list[str]

    def __str__(self) -> str:
        lines = [
            f"[{self.rank}] {self.title}  (score={self.score:.3f})",
            f"    URL: {self.url}",
        ]
        if self.component_name:
            lines.append(f"    Component: {self.component_name}")
        if self.headings_context:
            lines.append(f"    Context: {' > '.join(self.headings_context)}")
        if self.is_code:
            lines.append("    [code snippet]")
        lines.append(f"    {self.text[:300]}{'...' if len(self.text) > 300 else ''}")
        return "\n".join(lines)


class MUISearch:
    """
    Semantic search over the MUI documentation vector database.

    Usage:
        searcher = MUISearch.from_index("index/")
        results = searcher.search("how to style a button with custom colors")
        for r in results:
            print(r)
    """

    def __init__(self, store: VectorStore, model_name: str = DEFAULT_MODEL):
        self._store = store
        self._model_name = model_name

    @classmethod
    def from_index(
        cls,
        index_dir: str | Path = "index",
        model_name: str = DEFAULT_MODEL,
    ) -> "MUISearch":
        store = VectorStore.load(Path(index_dir))
        return cls(store, model_name)

    def search(
        self,
        query: str,
        top_k: int = 8,
        section: Optional[str] = None,
        include_code: bool = True,
        score_threshold: float = 0.2,
        dedupe_urls: bool = True,
    ) -> list[SearchResult]:
        """
        Semantic search over MUI docs.

        Args:
            query: Natural language query.
            top_k: Number of results to return.
            section: Filter by section ("component", "customization",
                     "getting-started"). None = all sections.
            include_code: Whether to include code snippet chunks.
            score_threshold: Minimum cosine similarity score (0–1).
            dedupe_urls: If True, return at most one result per URL.

        Returns:
            List of SearchResult ordered by descending score.
        """
        q_vec = embed_query(query, model_name=self._model_name)

        if section:
            raw = self._store.search_by_section(q_vec, section, top_k=top_k * 4)
        else:
            raw = self._store.search(q_vec, top_k=top_k * 4, score_threshold=score_threshold)

        results: list[SearchResult] = []
        seen_urls: set[str] = set()

        for chunk, score in raw:
            if score < score_threshold:
                continue
            if not include_code and chunk.is_code:
                continue
            if dedupe_urls and chunk.url in seen_urls:
                continue
            seen_urls.add(chunk.url)

            results.append(
                SearchResult(
                    rank=len(results) + 1,
                    score=score,
                    chunk_id=chunk.chunk_id,
                    url=chunk.url,
                    title=chunk.title,
                    component_name=chunk.component_name,
                    section=chunk.section,
                    is_code=chunk.is_code,
                    text=chunk.text,
                    headings_context=chunk.headings_context,
                )
            )

            if len(results) >= top_k:
                break

        return results

    def search_component(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Convenience: search only within component documentation."""
        return self.search(query, top_k=top_k, section="component")

    def search_customization(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Convenience: search only within customization documentation."""
        return self.search(query, top_k=top_k, section="customization")

    def stats(self) -> dict:
        return self._store.stats()
