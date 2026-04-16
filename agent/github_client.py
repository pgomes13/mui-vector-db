"""
Thin wrapper around the GitHub REST API.

Only the three calls the agent actually needs:
  - get_pr_metadata   → PR title, author, numbers
  - get_pr_files      → changed files with per-file patches
  - post_review_comment → post a comment on the PR
"""

import requests

_API = "https://api.github.com"


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _check(resp: requests.Response, context: str) -> None:
    if not resp.ok:
        raise RuntimeError(
            f"GitHub API error ({context}): "
            f"{resp.status_code} {resp.text[:300]}"
        )


def get_pr_metadata(repo: str, pr_number: int, token: str) -> dict:
    """Return title, author login, and base/head info for a PR."""
    url = f"{_API}/repos/{repo}/pulls/{pr_number}"
    resp = requests.get(url, headers=_headers(token), timeout=15)
    _check(resp, f"get_pr_metadata {repo}#{pr_number}")
    data = resp.json()
    return {
        "number": data["number"],
        "title": data["title"],
        "author": data["user"]["login"],
        "base": data["base"]["ref"],
        "head": data["head"]["ref"],
        "url": data["html_url"],
    }


def get_pr_files(repo: str, pr_number: int, token: str) -> list[dict]:
    """
    Return the list of changed files for a PR.
    Each entry has: filename, status, additions, deletions, patch (may be absent
    for binary files or very large diffs).
    Handles pagination automatically (up to 300 files).
    """
    files: list[dict] = []
    page = 1
    while True:
        url = f"{_API}/repos/{repo}/pulls/{pr_number}/files"
        resp = requests.get(
            url,
            headers=_headers(token),
            params={"per_page": 100, "page": page},
            timeout=15,
        )
        _check(resp, f"get_pr_files {repo}#{pr_number} page={page}")
        batch = resp.json()
        if not batch:
            break
        files.extend(batch)
        if len(batch) < 100:
            break
        page += 1
        if page > 3:  # cap at 300 files
            break
    return files


def post_review_comment(
    repo: str, pr_number: int, token: str, body: str
) -> None:
    """Post a single PR-level comment (not an inline review comment)."""
    url = f"{_API}/repos/{repo}/issues/{pr_number}/comments"
    resp = requests.post(
        url,
        headers=_headers(token),
        json={"body": body},
        timeout=15,
    )
    _check(resp, f"post_review_comment {repo}#{pr_number}")
