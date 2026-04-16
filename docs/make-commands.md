# Make commands

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
