# MUI Vector DB

Semantic search over the [Material UI](https://mui.com/material-ui/) documentation.

Scrapes 60+ MUI component and guide pages, chunks the text, embeds it with
[sentence-transformers](https://www.sbert.net/), and stores it in a
[FAISS](https://github.com/facebookresearch/faiss) index for fast cosine-similarity
search.

## Quick start

```bash
# 1. Build the index (first run ~3–5 min)
make build

# 2. Search interactively
make search

# 3. One-shot query
make query Q="how to add a loading spinner to a button"
```

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

## Docs

- [Architecture & project layout](docs/architecture.md)
- [Make commands](docs/make-commands.md)
- [Search API](docs/search-api.md)
