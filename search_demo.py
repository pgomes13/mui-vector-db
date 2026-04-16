#!/usr/bin/env python3
"""
Interactive search demo for the MUI vector database.

Usage:
    # One-shot query:
    python search_demo.py "how to add a loading spinner to a button"

    # Interactive REPL:
    python search_demo.py

    # Filter to a section:
    python search_demo.py --section component "autocomplete with async data"
"""

import argparse
import sys
from pathlib import Path

INDEX_DIR = Path("index")

SAMPLE_QUERIES = [
    "how to add a loading spinner to a button",
    "customize the primary color in the theme",
    "controlled vs uncontrolled TextField",
    "responsive grid layout breakpoints",
    "show a confirmation dialog",
    "autocomplete with async fetch",
    "sticky app bar on scroll",
    "dark mode toggle",
    "virtualized list for large datasets",
    "custom styled component with sx prop",
]


def format_result(r, verbose: bool = False) -> str:
    lines = [
        f"\n{'─' * 60}",
        f"[{r.rank}] {r.title}  (score={r.score:.3f})",
        f"    {r.url}",
    ]
    if r.component_name:
        lines.append(f"    Component: {r.component_name}")
    if r.headings_context:
        lines.append(f"    Section:   {' > '.join(r.headings_context)}")
    if r.is_code:
        lines.append("    [code snippet]")

    snippet = r.text if verbose else r.text[:400]
    if not verbose and len(r.text) > 400:
        snippet += "..."
    lines.append(f"\n    {snippet}")
    return "\n".join(lines)


def run_query(searcher, query: str, top_k: int, section, verbose: bool) -> None:
    print(f"\nQuery: \"{query}\"")
    results = searcher.search(
        query,
        top_k=top_k,
        section=section,
        include_code=True,
    )
    if not results:
        print("  No results found.")
        return
    for r in results:
        print(format_result(r, verbose=verbose))
    print(f"\n{'─' * 60}")
    print(f"Found {len(results)} result(s).")


def interactive_repl(searcher, top_k: int, section, verbose: bool) -> None:
    print("\nMUI Vector DB — Interactive Search")
    print("Type a query and press Enter. Type 'quit' or Ctrl-C to exit.")
    print("Commands: :stats | :samples | :section <name> | :verbose | :quit")
    print("─" * 60)

    current_section = section
    current_verbose = verbose

    while True:
        try:
            raw = input("\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            break

        if not raw:
            continue

        if raw.lower() in ("quit", "exit", ":quit"):
            print("Bye!")
            break

        if raw == ":stats":
            import json
            print(json.dumps(searcher.stats(), indent=2))
            continue

        if raw == ":samples":
            print("Sample queries:")
            for q in SAMPLE_QUERIES:
                print(f"  {q}")
            continue

        if raw == ":verbose":
            current_verbose = not current_verbose
            print(f"Verbose mode: {'on' if current_verbose else 'off'}")
            continue

        if raw.startswith(":section"):
            parts = raw.split(maxsplit=1)
            current_section = parts[1].strip() if len(parts) > 1 else None
            print(f"Section filter: {current_section or '(all)'}")
            continue

        run_query(searcher, raw, top_k, current_section, current_verbose)


def main() -> None:
    parser = argparse.ArgumentParser(description="Search the MUI vector database")
    parser.add_argument("query", nargs="?", help="Search query (omit for REPL mode)")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    parser.add_argument(
        "--section",
        choices=["component", "customization", "getting-started"],
        default=None,
        help="Limit results to a documentation section",
    )
    parser.add_argument("--verbose", action="store_true", help="Show full text")
    parser.add_argument(
        "--index-dir",
        default=str(INDEX_DIR),
        help=f"Path to the index directory (default: {INDEX_DIR})",
    )
    parser.add_argument(
        "--samples",
        action="store_true",
        help="Run sample queries and exit",
    )
    args = parser.parse_args()

    if not Path(args.index_dir).exists():
        print(f"Index not found at '{args.index_dir}'.")
        print("Run 'python build_index.py' first to build the index.")
        sys.exit(1)

    from src.search import MUISearch
    searcher = MUISearch.from_index(args.index_dir)

    if args.samples:
        for q in SAMPLE_QUERIES[:5]:
            run_query(searcher, q, args.top_k, args.section, args.verbose)
        return

    if args.query:
        run_query(searcher, args.query, args.top_k, args.section, args.verbose)
    else:
        interactive_repl(searcher, args.top_k, args.section, args.verbose)


if __name__ == "__main__":
    main()
