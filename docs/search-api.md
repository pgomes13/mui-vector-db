# Search API

## Basic usage

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

## `search()` options

| Parameter | Default | Description |
|---|---|---|
| `query` | — | Natural language query string |
| `top_k` | `8` | Number of results to return |
| `section` | `None` | `"component"`, `"customization"`, or `"getting-started"` |
| `include_code` | `True` | Include code snippet chunks |
| `score_threshold` | `0.2` | Minimum cosine similarity (0–1) |
| `dedupe_urls` | `True` | At most one result per doc page |

## `SearchResult` fields

| Field | Type | Description |
|---|---|---|
| `rank` | `int` | Position in results (1-based) |
| `score` | `float` | Cosine similarity 0–1 |
| `url` | `str` | Source doc URL |
| `title` | `str` | Page title |
| `component_name` | `str` | Component name, if applicable |
| `section` | `str` | `"component"`, `"customization"`, etc. |
| `is_code` | `bool` | Whether the chunk is a code snippet |
| `text` | `str` | Chunk text |
| `headings_context` | `list[str]` | Nearest headings above this chunk |
