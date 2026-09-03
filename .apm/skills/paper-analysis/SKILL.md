---
name: paper-analysis
description: Analyze a research paper from user-provided text, PDF, text file, or normalized paper-input JSON, with evidence-grounded summaries, structured facts, and author-stated future work.
---

# paper-analysis

This skill starts the registered `paper-analysis` agent. It accepts one of:

- Pasted abstract or full text
- An absolute local PDF path
- An absolute local `.txt` or `.md` path
- An absolute normalized JSON paper-input path

It does not search for papers, download papers, or own Zotero integration. Zotero-aware callers must normalize any fallback metadata/abstract upstream and pass only the resulting JSON file path.

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

`item_key` and `source` are provenance only; `paper-analysis` never uses them to open Zotero or an MCP session. The agent must run the absolute `scripts/paper_input.py` helper first and consume only its canonical JSON output afterwards.

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

## Full-mode structured facts contract

A saved `mode: full` run must produce all three sibling artifacts from one analysis invocation:

```text
<analysis>.md
<analysis>.md.facts.json
<analysis>.md.future_work.json
```

The facts sidecar is **not** a later Markdown extraction and must not trigger a second model pass over the paper. When spawning the registered `paper-analysis` agent for `mode: full`, include these instructions in the task prompt:

1. During the same three-way full-text analysis/synthesis that produces the Markdown, keep a compact `facts-draft.json` containing only facts already established in that pass. Do not re-open or re-read the paper solely for the draft, and do not regex/grep the final Markdown to reconstruct it.
2. The draft shape is:

   ```json
   {
     "paper": {"title":"...","authors":["..."],"year":2026,"venue":"...","doi":"..."},
     "research_problem": "...",
     "research_object": "...",
     "approach": "...",
     "findings": ["..."],
     "contributions": ["..."],
     "topic_terms": ["..."],
     "limitations": ["..."],
     "source_anchors": {
       "research_problem": ["§1 Introduction"],
       "approach": ["§3 Method"],
       "findings": ["§5 Results"]
     },
     "confidence": 0.0
   }
   ```

   `source_anchors` and `confidence` are optional. Never put `future_work_ids` in the model draft; those IDs are joined deterministically from the validated future-work sidecar.
3. Preserve the existing full-analysis Markdown quality and existing future-work evidence chain. For PDF full mode, run `future_work.py prepare` before/alongside analysis as already required, then after the Markdown exists run `future_work.py upgrade-full-sidecar` so `<analysis>.md.future_work.json` is validated against prepared candidates and contains stable IDs/page numbers.
4. Only after that future-work sidecar has `status: ok`, run:

   ```bash
   uv run "$FACTS_SCRIPT" validate --draft "<temp>/facts-draft.json"
   uv run "$FACTS_SCRIPT" finalize \
     --analysis "<analysis>.md" \
     --draft "<temp>/facts-draft.json" \
     --future-work "<analysis>.md.future_work.json" \
     --input "<stable-source-file>" \
     --evidence-level fulltext
   ```

   For normalized abstract input use the canonical JSON as `<stable-source-file>` and `--evidence-level abstract_only`. For pasted input first write the exact supplied text to a temporary stable source file and fingerprint that file. For PDF use the source PDF itself; OCR text may be analyzed, but the fingerprint remains tied to the PDF input.
5. Treat `facts.py` as the only writer/validator of `<analysis>.md.facts.json`. It supplies schema/version, source fingerprint, and exact `future_work_ids`; do not hand-write or patch that sidecar.
6. Return success for a saved full run only after both sidecars exist with `status: ok`. A validation/finalization failure is an error, not a reason to silently omit a sidecar.

This keeps `facts.json` compact enough for downstream `professor-contact` Stage 2/3 and lets callers detect staleness by `schema`, `generator_version`, and `input_fingerprint` without re-reading the PDF.

## Runtime

- Direct clone/development: run `uv sync` at the repository root. The project dependency is `pdf-processing-core`, which supplies both `import pdfx` and PyMuPDF transitively.
- Normalized JSON validator: run `uv run <absolute paper_input.py> <absolute-json-path>` and use only its canonical output.
- Full-mode PDF extraction/rendering: run `uv run <absolute pdf_runtime.py> extract ...` and `uv run <absolute pdf_runtime.py> render ...`. The PEP 723 helper bootstraps `pdf-processing-core`, so APM installations do not depend on host PyMuPDF.
- Standalone future-work helper: run `uv run <absolute future_work.py> ...`; PEP 723 metadata bootstraps `pdf-processing-core` without requiring a synced checkout.
- Structured facts helper: run `uv run <absolute facts.py> validate ...` / `finalize ...`. It has no third-party dependencies and never invokes a model or parses the analysis Markdown for facts.
- PDF quality CLI: invoke it through uv, e.g. `uv run --with "pdf-processing-core @ git+https://github.com/ScholarWorkflow/pdf-processing-core.git@main" pdfx quality "<PDF>" --json`. Do not assume a global `pdfx` executable.

## Boundaries

- Never infer author intent from a limitation or reader speculation.
- Never invent metadata, quotations, page numbers, citations, or structured facts.
- Never add a second full-paper model call solely to create `facts.json`.
- Never reconstruct structured facts by regex/grep over the human Markdown.
- Keep temporary and generated output outside the source tree unless the user explicitly selects an output directory.
- Consume the installed `pdf-processing-core` package/API only; do not depend on that repository's layout or an APM checkout path.
- Do not import PyMuPDF from the host Python in the agent; use the uv-managed PDF runtime helper.
- OCR behavior via `vision-tools` is unchanged.
