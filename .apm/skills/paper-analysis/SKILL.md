---
name: paper-analysis
description: Analyze a research paper from user-provided text, PDF, text file, or normalized paper-input JSON, with evidence-grounded summaries and author-stated future work.
---

# paper-analysis

This skill starts the registered `paper-analysis` agent. It accepts one of:

- Pasted abstract or full text
- An absolute local PDF path
- An absolute local `.txt` or `.md` path
- An absolute normalized JSON paper-input path

It does not search for papers, download papers, or own Zotero integration. Zotero-aware callers should normalize any fallback metadata/abstract upstream and pass only the resulting JSON file path. During the cross-repository migration window, the agent retains a deprecated Zotero-item compatibility branch so existing `professor-contact` releases do not break; new callers must not depend on it.

Normalized abstract-level JSON uses this contract:

```json
{
  "schema": 1,
  "kind": "paper-analysis-input",
  "level": "abstract",
  "source": "zotero",
  "item_key": "...",
  "metadata": {
    "title": "...",
    "authors": ["..."],
    "year": 2025,
    "venue": "...",
    "doi": "..."
  },
  "abstract": "..."
}
```

`item_key` and `source` are provenance only; `paper-analysis` never uses them to open Zotero or an MCP session.

## Input

Pass the agent a structured prompt containing:

```text
mode: full|gap-only
paper: <pasted text or absolute local path>
save: <optional output directory>
patch_analysis: <optional existing analysis path for gap-only>
ocr_policy: <optional gap-only OCR policy>
```

`gap-only` requires either `save` or `patch_analysis`. It extracts only author-stated future work and validates every quotation against prepared source evidence.

## Runtime

- Direct clone/development: run `uv sync` at the repository root. The project dependency is `pdf-processing-core`, which supplies both `import pdfx` and PyMuPDF transitively.
- Standalone future-work helper: run `uv run <absolute future_work.py> ...`; PEP 723 metadata bootstraps `pdf-processing-core` without requiring a synced checkout.
- PDF quality CLI: invoke it through uv, e.g. `uv run --with "pdf-processing-core @ git+https://github.com/ScholarWorkflow/pdf-processing-core.git@main" pdfx quality "<PDF>" --json`. Do not assume a global `pdfx` executable.

## Boundaries

- Never infer author intent from a limitation or reader speculation.
- Never invent metadata, quotations, page numbers, or citations.
- Keep temporary and generated output outside the source tree unless the user explicitly selects an output directory.
- Consume the installed `pdf-processing-core` package/API only; do not depend on that repository's layout or an APM checkout path.
- OCR behavior via `vision-tools` is unchanged.
