---
name: paper-analysis
description: Analyze a research paper from user-provided text, PDF, or text file, with evidence-grounded summaries and author-stated future work.
---

# paper-analysis

This skill starts the registered `paper-analysis` agent. It accepts one of:

- Pasted abstract or full text
- A local PDF path
- A local `.txt` or `.md` file
- A paper read through an available Zotero integration

It does not search for papers or download papers. When Zotero integration is
available, it may read the selected item's metadata and full text, and may
write an OCR attachment back to that same item. It never writes account details,
service endpoints, local database paths, or item identifiers into analysis
output. Optional output is written only to an explicit user-selected directory.

## Input

Pass the agent a structured prompt containing:

```text
mode: full|gap-only
paper: <pasted text or local path>
save: <optional output directory>
patch_analysis: <optional existing analysis path for gap-only>
ocr_policy: <optional gap-only OCR policy>
```

`gap-only` requires either `save` or `patch_analysis`. It extracts only
author-stated future work and validates every quotation against prepared source
evidence.

## Boundaries

- Never infer author intent from a limitation or reader speculation.
- Never invent metadata, quotations, page numbers, or citations.
- Keep temporary and generated output outside the source tree unless the user
  explicitly selects an output directory.
- Use the installed PDF processing package for page quality checks.
