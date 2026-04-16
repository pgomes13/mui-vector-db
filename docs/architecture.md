# Architecture

## Pipeline

```
MUI docs (mui.com)
      │
      ▼
  scraper.py        HTTP + BeautifulSoup — saves pages to data/raw/*.json
      │
      ▼
  chunker.py        512-char overlapping chunks + separate code snippets
      │
      ▼
  embedder.py       sentence-transformers (all-MiniLM-L6-v2, 384-dim)
      │              → cached to data/processed/embeddings.npy
      ▼
  vector_store.py   FAISS IndexFlatIP (cosine sim on unit-norm vectors)
                     → index/faiss.index + index/metadata.json
```

At query time the same model embeds the query string, and FAISS returns the
nearest neighbours by cosine similarity.

## Project layout

```
mui-vector-db/
├── src/
│   ├── scraper.py       Crawl MUI docs, cache raw pages
│   ├── chunker.py       Split pages into overlapping text/code chunks
│   ├── embedder.py      Generate & cache sentence embeddings
│   ├── vector_store.py  FAISS index — build, save, load, search
│   └── search.py        MUISearch — high-level search API
├── build_index.py       Pipeline entry point
├── search_demo.py       CLI / interactive REPL
├── Makefile
└── requirements.txt
```

Generated at runtime (git-ignored):

```
data/raw/            Scraped JSON pages
data/processed/      Chunk JSON + embedding cache (.npy)
index/               FAISS index + metadata
.venv/               Python virtual environment
```

## Coverage

The index covers:

- **Components** — all ~50 Material UI component pages (Button, TextField,
  Autocomplete, Dialog, DataGrid, …)
- **Customization** — theming, palette, typography, spacing, breakpoints,
  dark mode, CSS variables
- **Getting started** — overview, installation, usage
