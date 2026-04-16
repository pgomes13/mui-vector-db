# MUI Vector DB

Semantic search over the [Material UI](https://mui.com/material-ui/) documentation,
plus an agent that reviews pull requests for non-conforming MUI usage and posts
corrective comments automatically.

## Quick start

```bash
# 1. Build the index (first run ~3–5 min)
make build

# 2. Search interactively
make search

# 3. One-shot query
make query Q="how to add a loading spinner to a button"
```

## PR review agent

The agent watches for PRs that touch `.tsx`/`.jsx` files, detects MUI component
imports in the diff, queries the vector DB for correct usage docs, and posts a
comment with specific fixes — powered by a local [Ollama](https://ollama.com) model
(no API key required).

```bash
# Pull the model once
make ollama-pull

# Dry-run on any PR (prints comment, does not post)
make review-dry REPO=owner/repo PR=42

# Live review (posts the comment)
make review REPO=owner/repo PR=42

# Use a different model
make review REPO=owner/repo PR=42 OLLAMA_MODEL=llama3.2
```

The [GitHub Actions workflow](.github/workflows/pr-review.yml) triggers
automatically on every PR that touches `.tsx`/`.jsx` files.

## Requirements

- Python 3.9+
- [Ollama](https://ollama.com) running locally for the review agent
- Internet access for the initial scrape

Dependencies are pinned in `requirements.txt`:

```
requests, beautifulsoup4, lxml    # scraping
sentence-transformers             # embeddings
faiss-cpu                         # vector index
tqdm                              # progress bars
ollama                            # local LLM for PR review
```

## Docs

- [Architecture & project layout](docs/architecture.md)
- [Make commands](docs/make-commands.md)
- [Search API](docs/search-api.md)
