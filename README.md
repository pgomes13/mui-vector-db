# MUI Vector DB

Semantic search over the [Material UI](https://mui.com/material-ui/) documentation.

Scrapes 60+ MUI component and guide pages, chunks the text, embeds it with
[sentence-transformers](https://www.sbert.net/), and stores it in a
[FAISS](https://github.com/facebookresearch/faiss) index for fast cosine-similarity
search.

---

## Quick start

```bash
# 1. Build the index (first run ~3–5 min)
make build

# 2. Search interactively
make search

# 3. One-shot query
make query Q="how to add a loading spinner to a button"
```

---

## How it works

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

---

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

---

## Make commands

| Command | Description |
|---|---|
| `make install` | Create `.venv` and install dependencies |
| `make build` | Full pipeline — scrape → chunk → embed → index |
| `make rebuild` | Same but ignores all caches |
| `make scrape` | Scrape docs only, skip embedding |
| `make search` | Interactive search REPL |
| `make query Q="..."` | One-shot query from the terminal |
| `make samples` | Run built-in sample queries |
| `make stats` | Print index statistics |
| `make clean-index` | Delete FAISS index (keeps scraped data) |
| `make clean-embeddings` | Delete embedding cache only |
| `make clean-data` | Delete all data and index |
| `make clean` | Remove `.venv` |
| `make clean-all` | Remove everything generated |

---

## Search API

```python
from src.search import MUISearch

searcher = MUISearch.from_index("index/")

# Semantic search across all sections
results = searcher.search("controlled vs uncontrolled TextField", top_k=5)

# Filter to component docs only
results = searcher.search_component("autocomplete with async fetch")

# Filter to customization docs only
results = searcher.search_customization("override primary palette color")

for r in results:
    print(r)          # formatted output with URL, score, snippet
    print(r.url)
    print(r.score)    # cosine similarity 0–1
    print(r.text)     # chunk text
```

### `search()` options

| Parameter | Default | Description |
|---|---|---|
| `query` | — | Natural language query string |
| `top_k` | `8` | Number of results to return |
| `section` | `None` | `"component"`, `"customization"`, or `"getting-started"` |
| `include_code` | `True` | Include code snippet chunks |
| `score_threshold` | `0.2` | Minimum cosine similarity (0–1) |
| `dedupe_urls` | `True` | At most one result per doc page |

---

## Coverage

The index covers:

- **Components** — all ~50 Material UI component pages (Button, TextField,
  Autocomplete, Dialog, DataGrid, …)
- **Customization** — theming, palette, typography, spacing, breakpoints,
  dark mode, CSS variables
- **Getting started** — overview, installation, usage

---

## Requirements

- Python 3.9+
- Internet access for the initial scrape

Dependencies are pinned in `requirements.txt`:

```
requests, beautifulsoup4, lxml    # scraping
sentence-transformers             # embeddings
faiss-cpu                         # vector index
tqdm                              # progress bars
```
