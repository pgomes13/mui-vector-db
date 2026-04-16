PYTHON     := python3
VENV       := .venv
PIP        := $(VENV)/bin/pip
PY         := $(VENV)/bin/python

INDEX_DIR  := index
RAW_DIR    := data/raw
PROC_DIR   := data/processed
OLLAMA_MODEL ?= qwen2.5-coder:7b

.DEFAULT_GOAL := help

# ── Help ──────────────────────────────────────────────────────────────────────

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Environment ───────────────────────────────────────────────────────────────

.PHONY: install
install: $(VENV)/bin/activate ## Create venv and install dependencies

$(VENV)/bin/activate: requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@touch $(VENV)/bin/activate

# ── Pipeline ──────────────────────────────────────────────────────────────────

.PHONY: build
build: install ## Scrape, chunk, embed, and build FAISS index (cached)
	$(PY) build_index.py

.PHONY: rebuild
rebuild: install ## Force full rebuild — ignores all caches
	$(PY) build_index.py --force

.PHONY: scrape
scrape: install ## Scrape MUI docs only (no embedding)
	$(PY) -c "from src.scraper import scrape_all; from pathlib import Path; scrape_all(Path('$(RAW_DIR)'))"

# ── Search ────────────────────────────────────────────────────────────────────

.PHONY: search
search: ## Launch interactive search REPL  (make search)
	$(PY) search_demo.py

.PHONY: query
query: ## One-shot query: make query Q="your question here"
ifndef Q
	$(error Q is required — usage: make query Q="your question")
endif
	$(PY) search_demo.py "$(Q)"

.PHONY: samples
samples: ## Run the built-in sample queries
	$(PY) search_demo.py --samples

# ── Data management ───────────────────────────────────────────────────────────

.PHONY: clean-index
clean-index: ## Delete the FAISS index (keeps scraped data)
	rm -rf $(INDEX_DIR)

.PHONY: clean-embeddings
clean-embeddings: ## Delete cached embeddings (keeps raw scrape)
	rm -f $(PROC_DIR)/embeddings.npy

.PHONY: clean-data
clean-data: ## Delete all scraped + processed data and index
	rm -rf $(RAW_DIR) $(PROC_DIR) $(INDEX_DIR)

.PHONY: clean
clean: ## Remove venv (keeps scraped data and index)
	rm -rf $(VENV)

.PHONY: clean-all
clean-all: clean clean-data ## Remove everything generated

# ── Agent ─────────────────────────────────────────────────────────────────────

.PHONY: review
review: ## Review a PR: make review REPO=owner/repo PR=42
ifndef REPO
	$(error REPO is required — usage: make review REPO=owner/repo PR=42)
endif
ifndef PR
	$(error PR is required — usage: make review REPO=owner/repo PR=42)
endif
	OLLAMA_MODEL=$(OLLAMA_MODEL) $(PY) -m agent.pipeline --repo "$(REPO)" --pr $(PR) --index-dir $(INDEX_DIR)

.PHONY: review-dry
review-dry: ## Dry-run review (prints comment, does not post): make review-dry REPO=owner/repo PR=42
ifndef REPO
	$(error REPO is required — usage: make review-dry REPO=owner/repo PR=42)
endif
ifndef PR
	$(error PR is required — usage: make review-dry REPO=owner/repo PR=42)
endif
	OLLAMA_MODEL=$(OLLAMA_MODEL) $(PY) -m agent.pipeline --repo "$(REPO)" --pr $(PR) --index-dir $(INDEX_DIR) --dry-run

.PHONY: ollama-pull
ollama-pull: ## Pull the default Ollama model (qwen2.5-coder:7b)
	ollama pull $(OLLAMA_MODEL)

# ── Stats ─────────────────────────────────────────────────────────────────────

.PHONY: stats
stats: ## Print index statistics
	$(PY) -c "from src.search import MUISearch; import json; print(json.dumps(MUISearch.from_index().stats(), indent=2))"
