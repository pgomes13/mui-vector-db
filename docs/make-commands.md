# Make commands

## Environment

| Command | Description |
|---|---|
| `make install` | Create `.venv` and install dependencies |

## Index pipeline

| Command | Description |
|---|---|
| `make build` | Full pipeline — scrape → chunk → embed → index |
| `make rebuild` | Same but ignores all caches |
| `make scrape` | Scrape docs only, skip embedding |

## Search

| Command | Description |
|---|---|
| `make search` | Interactive search REPL |
| `make query Q="..."` | One-shot query from the terminal |
| `make samples` | Run built-in sample queries |
| `make stats` | Print index statistics |

## PR review agent

| Command | Description |
|---|---|
| `make ollama-pull` | Pull the default Ollama model (`qwen2.5-coder:7b`) |
| `make review REPO=owner/repo PR=42` | Review a PR and post a comment |
| `make review-dry REPO=owner/repo PR=42` | Dry-run — print comment without posting |

Override the model with `OLLAMA_MODEL=llama3.2` on any agent command.

## Cleanup

| Command | Description |
|---|---|
| `make clean-index` | Delete FAISS index (keeps scraped data) |
| `make clean-embeddings` | Delete embedding cache only |
| `make clean-data` | Delete all data and index |
| `make clean` | Remove `.venv` |
| `make clean-all` | Remove everything generated |
