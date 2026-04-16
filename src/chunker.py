"""
Text chunker for MUI documentation pages.

Splits scraped pages into overlapping chunks suitable for embedding.
Each chunk carries metadata so search results can be traced back to
the original page.
"""

import re
from dataclasses import dataclass, field, asdict
from typing import Optional

from .scraper import ScrapedPage

# Tuning knobs
DEFAULT_CHUNK_SIZE = 512    # target characters per chunk
DEFAULT_OVERLAP = 64        # overlap between consecutive chunks
MIN_CHUNK_LENGTH = 80       # discard chunks shorter than this


@dataclass
class Chunk:
    chunk_id: str           # e.g. "react-button_0"
    url: str
    title: str
    section: str
    component_name: str
    chunk_index: int
    text: str
    headings_context: list[str] = field(default_factory=list)
    is_code: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Chunk":
        return cls(**d)


def _make_id(page: ScrapedPage, index: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", page.url.lower()).strip("-")
    # Keep only the last meaningful segment to keep IDs short
    parts = [p for p in slug.split("-") if p]
    short = "-".join(parts[-6:]) if len(parts) > 6 else slug
    return f"{short}_{index}"


def _split_into_sentences(text: str) -> list[str]:
    """Rough sentence splitter that preserves newlines as natural breaks."""
    # Split on sentence-ending punctuation or blank lines
    parts = re.split(r"(?<=[.!?])\s+|\n{2,}", text)
    return [p.strip() for p in parts if p.strip()]


def _chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[str]:
    """Split text into overlapping chunks of approximately chunk_size chars."""
    sentences = _split_into_sentences(text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        sentence_len = len(sentence)

        if current_len + sentence_len > chunk_size and current:
            chunk_text = " ".join(current)
            chunks.append(chunk_text)

            # Roll back by overlap characters
            overlap_sentences: list[str] = []
            overlap_len = 0
            for s in reversed(current):
                if overlap_len + len(s) <= overlap:
                    overlap_sentences.insert(0, s)
                    overlap_len += len(s)
                else:
                    break
            current = overlap_sentences
            current_len = overlap_len

        current.append(sentence)
        current_len += sentence_len

    if current:
        chunks.append(" ".join(current))

    return chunks


def _active_headings(headings: list[str], text: str) -> list[str]:
    """Return headings that appear in (or just before) the chunk text."""
    # Simple heuristic: include headings whose text overlaps with chunk words
    chunk_words = set(text.lower().split())
    relevant = []
    for h in headings:
        h_words = set(h.lower().split())
        if len(h_words & chunk_words) >= max(1, len(h_words) // 2):
            relevant.append(h)
    return relevant[:3]  # cap at 3


def chunk_page(
    page: ScrapedPage,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    chunks: list[Chunk] = []

    # --- Prose content ---
    text_chunks = _chunk_text(page.content, chunk_size, overlap)
    for i, text in enumerate(text_chunks):
        if len(text) < MIN_CHUNK_LENGTH:
            continue
        chunks.append(
            Chunk(
                chunk_id=_make_id(page, len(chunks)),
                url=page.url,
                title=page.title,
                section=page.section,
                component_name=page.component_name,
                chunk_index=len(chunks),
                text=text,
                headings_context=_active_headings(page.headings, text),
                is_code=False,
            )
        )

    # --- Code examples (each is its own chunk) ---
    for code in page.code_examples:
        if len(code) < MIN_CHUNK_LENGTH:
            continue
        # Truncate very long code blocks
        code_text = code[:chunk_size * 2]
        # Prepend component name so embedding captures context
        prefix = f"{page.title} code example:\n" if page.title else "code example:\n"
        chunks.append(
            Chunk(
                chunk_id=_make_id(page, len(chunks)),
                url=page.url,
                title=page.title,
                section=page.section,
                component_name=page.component_name,
                chunk_index=len(chunks),
                text=prefix + code_text,
                headings_context=[page.title] if page.title else [],
                is_code=True,
            )
        )

    return chunks


def chunk_pages(
    pages: list[ScrapedPage],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    all_chunks: list[Chunk] = []
    for page in pages:
        all_chunks.extend(chunk_page(page, chunk_size, overlap))
    print(f"Produced {len(all_chunks)} chunks from {len(pages)} pages.")
    return all_chunks
