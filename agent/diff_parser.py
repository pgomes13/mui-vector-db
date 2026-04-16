"""
Parse GitHub PR file patches to extract MUI component usages.

Only added lines (+) are inspected — pre-existing imports are never re-flagged.
Filters to .tsx and .jsx files; skips removed files.
"""

import re
from dataclasses import dataclass, field

# Match: import { Button, TextField } from '@mui/material'
_NAMED_IMPORT = re.compile(
    r"^[+]?\s*import\s+\{([^}]+)\}\s+from\s+['\"](@mui/[^'\"]+)['\"]",
    re.MULTILINE,
)
# Match: import Button from '@mui/material/Button'
_DEFAULT_IMPORT = re.compile(
    r"^[+]?\s*import\s+(\w+)\s+from\s+['\"](@mui/[^'\"]+)['\"]",
    re.MULTILINE,
)

_CONTEXT_WINDOW = 10   # lines of surrounding context to send to the LLM
_IGNORE_MARKER = "mui-review-ignore"


@dataclass
class MUIUsage:
    file: str
    component_name: str     # e.g. "Button"
    package: str            # e.g. "@mui/material"
    import_line: str        # the raw import statement
    added_lines: list[str] = field(default_factory=list)   # all + lines in the patch
    context_lines: list[str] = field(default_factory=list) # lines near the import


def parse_pr_files(files: list[dict]) -> list[MUIUsage]:
    """
    Accept the list of file objects returned by the GitHub
    GET /repos/{owner}/{repo}/pulls/{pr}/files endpoint.
    Return a flat list of MUIUsage objects for all added MUI imports.
    """
    usages: list[MUIUsage] = []
    for f in files:
        filename: str = f.get("filename", "")
        status: str = f.get("status", "")
        patch: str = f.get("patch", "") or ""

        if status == "removed":
            continue
        if not (filename.endswith(".tsx") or filename.endswith(".jsx")):
            continue
        if not patch:
            continue

        usages.extend(_extract_mui_usages(filename, patch))

    return usages


def _extract_mui_usages(filename: str, patch: str) -> list[MUIUsage]:
    lines = patch.splitlines()
    added_lines = [l[1:].strip() for l in lines if l.startswith("+")]

    # Build a compact view of all + lines for context lookup
    usages: list[MUIUsage] = []
    seen: set[str] = set()  # (filename, component_name) — one entry per component

    for i, raw_line in enumerate(lines):
        # Only process lines that were added in this PR
        if not raw_line.startswith("+"):
            continue

        line = raw_line[1:]  # strip leading +

        if _IGNORE_MARKER in line:
            continue

        # Collect context: surrounding raw lines (both + and context)
        start = max(0, i - _CONTEXT_WINDOW)
        end = min(len(lines), i + _CONTEXT_WINDOW + 1)
        context = [l.lstrip("+- ") for l in lines[start:end]]

        # Try named import: { Button, TextField }
        for m in _NAMED_IMPORT.finditer(line):
            names_str, package = m.group(1), m.group(2)
            components = _parse_named_components(names_str)
            for comp in components:
                key = (filename, comp)
                if key in seen:
                    continue
                seen.add(key)
                usages.append(MUIUsage(
                    file=filename,
                    component_name=comp,
                    package=package,
                    import_line=line.strip(),
                    added_lines=added_lines,
                    context_lines=context,
                ))

        # Try default import: import Button from '@mui/material/Button'
        for m in _DEFAULT_IMPORT.finditer(line):
            comp, package = m.group(1), m.group(2)
            # Skip if this line was already matched by named import
            if "{" in line:
                continue
            key = (filename, comp)
            if key in seen:
                continue
            seen.add(key)
            usages.append(MUIUsage(
                file=filename,
                component_name=comp,
                package=package,
                import_line=line.strip(),
                added_lines=added_lines,
                context_lines=context,
            ))

    return usages


def _parse_named_components(names_str: str) -> list[str]:
    """
    Extract component names from the braces of a named import.
    Handles aliases: `Button as MuiButton` → "Button".
    """
    components = []
    for part in names_str.split(","):
        part = part.strip()
        if not part:
            continue
        # Strip alias: "Button as Btn" → "Button"
        name = part.split(" as ")[0].strip()
        if name and name[0].isupper():  # MUI exports are PascalCase
            components.append(name)
    return components
