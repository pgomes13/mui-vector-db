"""All prompt templates used by the MUI PR review agent."""

SYSTEM_PROMPT = """\
You are a Material UI (MUI) code reviewer. Your job is to detect non-conforming \
MUI component usage in a pull request diff and provide specific, actionable \
corrective guidance.

Rules:
- Only flag real violations, not stylistic preferences.
- Ground every finding in the retrieved documentation excerpts provided.
- If the code matches the documented correct usage, respond with exactly: NO_ISSUES
- Do not hallucinate API props or patterns not present in the docs.
- Be concise: one finding per component, with a corrected code snippet.\
"""

ANALYSIS_PROMPT = """\
Component: {component_name}
Package: {package}
File: {file}

## Code from Pull Request (added lines)
```tsx
{added_code}
```

## MUI Documentation Excerpts
{docs_text}

## Task
Review the PR code for this component against the documentation excerpts above.
Identify any non-conforming usage patterns. For each issue found, provide:
1. A one-sentence description of what is wrong.
2. The correct usage as a tsx code snippet.
3. The MUI docs URL where the correct pattern is documented.

If the usage looks correct based on the docs, respond with exactly: NO_ISSUES\
"""

COMMENT_HEADER = """\
## MUI Usage Review

> Automated review powered by [MUI Vector DB](../../) + Ollama (`{model}`).
> {issue_count} issue(s) found across {component_count} component(s).

"""

FINDING_TEMPLATE = """\
### `{component_name}` in `{file}`

{analysis}

"""

COMMENT_FOOTER = """\
---
*To suppress this comment for a specific line, add `// mui-review-ignore` on the \
import line.*\
"""
