"""
Analyze MUI component usages against retrieved docs using a local Ollama model.

One Ollama call per unique component name. Returns a list of finding dicts
for components where non-conforming usage was detected.
"""

import os
from typing import Optional

import ollama

from .diff_parser import MUIUsage
from .prompts import SYSTEM_PROMPT, ANALYSIS_PROMPT

DEFAULT_MODEL = "qwen2.5-coder:7b"
_MAX_DOC_RESULTS = 5
_MAX_DOC_CHARS = 600   # truncate each doc chunk to this length


def _build_docs_text(results) -> str:
    """Format SearchResult list into a prompt-friendly string."""
    parts = []
    for r in results[:_MAX_DOC_RESULTS]:
        text = r.text[:_MAX_DOC_CHARS]
        if len(r.text) > _MAX_DOC_CHARS:
            text += "..."
        label = "[code]" if r.is_code else "[docs]"
        parts.append(f"### {r.title} {label}\nURL: {r.url}\n{text}")
    return "\n\n".join(parts)


def _call_ollama(prompt: str, model: str, host: Optional[str]) -> str:
    """Call Ollama chat API and return the response text."""
    client = ollama.Client(host=host) if host else ollama.Client()
    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        options={"temperature": 0.1},  # low temp for deterministic code review
    )
    return response["message"]["content"].strip()


def analyze_usage(
    usage: MUIUsage,
    docs,               # list[SearchResult]
    model: str,
    host: Optional[str],
) -> Optional[dict]:
    """
    Analyze a single MUIUsage against retrieved docs.
    Returns a finding dict or None if no issues detected.
    """
    added_code = "\n".join(usage.added_lines[:50])  # cap to avoid huge prompts
    docs_text = _build_docs_text(docs)

    if not docs_text:
        docs_text = "(No documentation found for this component in the vector DB.)"

    prompt = ANALYSIS_PROMPT.format(
        component_name=usage.component_name,
        package=usage.package,
        file=usage.file,
        added_code=added_code,
        docs_text=docs_text,
    )

    response = _call_ollama(prompt, model, host)

    if response.strip() == "NO_ISSUES":
        return None

    return {
        "component": usage.component_name,
        "file": usage.file,
        "analysis": response,
        "doc_urls": list({r.url for r in docs}),
    }


def analyze_all_usages(
    usages: list[MUIUsage],
    searcher,           # MUISearch
    model: Optional[str] = None,
    host: Optional[str] = None,
) -> list[dict]:
    """
    Analyze all MUI usages. Deduplicates by component name so the same
    component is only analyzed once even if imported in multiple files.
    Returns list of finding dicts (empty = no issues).
    """
    model = model or os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)
    host = host or os.environ.get("OLLAMA_HOST") or None

    # Dedupe: one analysis per component name, but accumulate all files
    by_component: dict[str, MUIUsage] = {}
    component_files: dict[str, list[str]] = {}
    for u in usages:
        if u.component_name not in by_component:
            by_component[u.component_name] = u
            component_files[u.component_name] = []
        if u.file not in component_files[u.component_name]:
            component_files[u.component_name].append(u.file)

    findings: list[dict] = []
    for comp, usage in by_component.items():
        # Retrieve docs from two angles and merge
        results_a = searcher.search(
            f"{comp} {usage.package} usage props API",
            top_k=_MAX_DOC_RESULTS,
            include_code=True,
        )
        results_b = searcher.search_component(comp, top_k=3)

        seen_urls: set[str] = set()
        merged = []
        for r in results_a + results_b:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                merged.append(r)

        print(f"  Analyzing {comp} ({len(merged)} doc chunks)...")
        finding = analyze_usage(usage, merged, model, host)
        if finding:
            # Attach all files where this component was found
            finding["files"] = component_files[comp]
            findings.append(finding)

    return findings
