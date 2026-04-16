#!/usr/bin/env python3
"""
Build the MUI documentation vector index.

Pipeline:
  1. Scrape MUI docs  →  data/raw/*.json
  2. Chunk text       →  data/processed/chunks.json
  3. Embed chunks     →  data/processed/embeddings.npy  (cached)
  4. Build FAISS index → index/faiss.index + index/metadata.json

Run once (takes ~3-5 min on first run due to scraping + embedding):
    python build_index.py

Subsequent runs are fast — scraper caches pages and embedder caches vectors.
To force a full rebuild:
    python build_index.py --force
"""

import argparse
import json
from pathlib import Path

from src.scraper import scrape_all, load_raw
from src.chunker import chunk_pages
from src.embedder import embed_chunks, embedding_dim, DEFAULT_MODEL
from src.vector_store import VectorStore

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
INDEX_DIR = Path("index")
CHUNKS_FILE = PROCESSED_DIR / "chunks.json"
EMBEDDINGS_CACHE = PROCESSED_DIR / "embeddings.npy"


def main(force: bool = False, model: str = DEFAULT_MODEL) -> None:
    # ------------------------------------------------------------------ #
    # Step 1: Scrape
    # ------------------------------------------------------------------ #
    print("=" * 60)
    print("STEP 1: Scraping MUI documentation")
    print("=" * 60)
    pages = scrape_all(RAW_DIR)

    if not pages:
        print("No pages scraped. Check your network connection.")
        return

    # ------------------------------------------------------------------ #
    # Step 2: Chunk
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 60)
    print("STEP 2: Chunking pages")
    print("=" * 60)

    if CHUNKS_FILE.exists() and not force:
        print(f"Loading cached chunks from {CHUNKS_FILE}")
        with open(CHUNKS_FILE) as f:
            raw_chunks = json.load(f)
        from src.chunker import Chunk
        chunks = [Chunk.from_dict(d) for d in raw_chunks]
        print(f"Loaded {len(chunks)} chunks.")
    else:
        chunks = chunk_pages(pages)
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        with open(CHUNKS_FILE, "w") as f:
            json.dump([c.to_dict() for c in chunks], f)
        print(f"Saved {len(chunks)} chunks to {CHUNKS_FILE}")

    if not chunks:
        print("No chunks produced. Check the scraper output.")
        return

    # ------------------------------------------------------------------ #
    # Step 3: Embed
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 60)
    print(f"STEP 3: Embedding with model '{model}'")
    print("=" * 60)

    cache = None if force else EMBEDDINGS_CACHE
    embeddings = embed_chunks(chunks, cache_path=cache, model_name=model)

    # ------------------------------------------------------------------ #
    # Step 4: Build FAISS index
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 60)
    print("STEP 4: Building FAISS index")
    print("=" * 60)

    dim = embeddings.shape[1]
    store = VectorStore(dim)
    store.add(chunks, embeddings)
    store.save(INDEX_DIR)

    # ------------------------------------------------------------------ #
    # Summary
    # ------------------------------------------------------------------ #
    print("\n" + "=" * 60)
    print("BUILD COMPLETE")
    print("=" * 60)
    stats = store.stats()
    print(f"Total vectors : {stats['total_vectors']}")
    print(f"Dimension     : {stats['dim']}")
    print(f"Sections      : {stats['sections']}")
    print(f"\nTop components by chunk count:")
    for name, count in stats["top_components"][:10]:
        print(f"  {name:<30} {count} chunks")
    print(f"\nIndex written to: {INDEX_DIR}/")
    print("Run `python search_demo.py` to try a search.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build MUI vector index")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-scrape and re-embed (ignore caches)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Sentence-transformers model name (default: {DEFAULT_MODEL})",
    )
    args = parser.parse_args()
    main(force=args.force, model=args.model)
