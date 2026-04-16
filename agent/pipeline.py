"""
MUI PR Review Agent — pipeline entry point.

Usage:
    python -m agent.pipeline --repo "owner/repo" --pr 42
    python -m agent.pipeline --repo "owner/repo" --pr 42 --dry-run
"""

import argparse
import os
import sys
from pathlib import Path

from . import github_client, diff_parser, analyzer, comment_formatter
from .analyzer import DEFAULT_MODEL


def run(
    repo: str,
    pr_number: int,
    index_dir: str = "index",
    dry_run: bool = False,
) -> int:
    """
    Run the full review pipeline for a single PR.

    Returns the number of findings posted (0 = clean PR).
    """
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("ERROR: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        return 1

    model = os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)
    ollama_host = os.environ.get("OLLAMA_HOST") or None

    # ── 1. Load the vector search index ──────────────────────────────────
    print(f"Loading MUI index from '{index_dir}'...")
    from src.search import MUISearch
    searcher = MUISearch.from_index(index_dir)

    # ── 2. Fetch PR data from GitHub ──────────────────────────────────────
    print(f"Fetching PR {repo}#{pr_number}...")
    pr_meta = github_client.get_pr_metadata(repo, pr_number, token)
    print(f"  Title : {pr_meta['title']}")
    print(f"  Author: {pr_meta['author']}")

    files = github_client.get_pr_files(repo, pr_number, token)
    print(f"  Files : {len(files)} changed")

    # ── 3. Parse MUI usages from diff ────────────────────────────────────
    usages = diff_parser.parse_pr_files(files)
    if not usages:
        print("No MUI component imports found in PR diff. Nothing to review.")
        return 0

    components = sorted({u.component_name for u in usages})
    print(f"  MUI components detected: {', '.join(components)}")

    # ── 4. Analyze each component via Ollama ─────────────────────────────
    print(f"\nAnalyzing with model '{model}'...")
    findings = analyzer.analyze_all_usages(
        usages,
        searcher,
        model=model,
        host=ollama_host,
    )

    if not findings:
        print("No MUI violations found. PR looks good!")
        return 0

    print(f"\nFound {len(findings)} issue(s).")

    # ── 5. Format and post comment ────────────────────────────────────────
    comment = comment_formatter.format_comment(findings, pr_meta, model)

    if dry_run:
        print("\n── DRY RUN — comment that would be posted ──")
        print(comment)
        print("── END DRY RUN ──")
        return len(findings)

    github_client.post_review_comment(repo, pr_number, token, comment)
    print(f"Posted review comment on {repo}#{pr_number}.")
    return len(findings)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Review a GitHub PR for MUI usage conformance"
    )
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--pr", type=int, required=True, help="PR number")
    parser.add_argument(
        "--index-dir", default="index", help="Path to FAISS index directory"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the comment instead of posting it",
    )
    args = parser.parse_args()
    sys.exit(run(args.repo, args.pr, args.index_dir, args.dry_run))


if __name__ == "__main__":
    main()
