"""
Assemble findings into a single GitHub PR comment (Markdown).
Returns None when there are no findings — signals the pipeline to skip posting.
"""

from typing import Optional

from .prompts import COMMENT_HEADER, FINDING_TEMPLATE, COMMENT_FOOTER


def format_comment(
    findings: list[dict],
    pr_meta: dict,
    model: str,
) -> Optional[str]:
    """
    Build the full Markdown comment string from a list of finding dicts.

    Each finding dict has:
        component  str
        file       str         (primary file)
        files      list[str]   (all files where the component appears)
        analysis   str         (raw LLM response)
        doc_urls   list[str]

    Returns None if findings is empty.
    """
    if not findings:
        return None

    unique_components = {f["component"] for f in findings}
    header = COMMENT_HEADER.format(
        model=model,
        issue_count=len(findings),
        component_count=len(unique_components),
    )

    sections: list[str] = []
    for f in findings:
        files_str = ", ".join(f"*{fn}*" for fn in f.get("files", [f["file"]]))
        sections.append(
            FINDING_TEMPLATE.format(
                component_name=f["component"],
                file=files_str,
                analysis=f["analysis"],
            )
        )

    return header + "\n".join(sections) + "\n" + COMMENT_FOOTER
