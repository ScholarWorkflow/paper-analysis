---
name: paper-analysis
description: Analyze a research paper from user-provided text, PDF, text file, or normalized paper-input JSON, with evidence-grounded summaries, structured facts for saved PDF full mode, and author-stated future work.
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

`gap-only` requires either `save` or `patch_analysis`. It extracts only author-stated future work and validates every quotation against prepared source evidence. Give the existing model the short candidate hints first; a user-specified page/section or insufficient hints may require only the necessary, not-yet-read local `source_pages`. Do not send the entire paper again or add another analysis process. Unread pages cannot support a claim that the whole paper has no future work; report incomplete when needed text or OCR authorization is unavailable. Pass the new `prepare.json` through `--candidates` to `validate` and `finalize`; the old candidates-only interface remains available with its original limits.

## Saved PDF full-mode structured facts contract

A saved `mode: full` run whose source is a **local PDF** must produce all three sibling artifacts from one analysis invocation:

```text
<analysis>.md
<analysis>.md.facts.json
<analysis>.md.future_work.json
```

This three-artifact contract is intentionally limited to local-PDF full mode because the existing validated full-mode future-work chain is PDF-backed. Pasted text, `.txt/.md`, and normalized abstract JSON retain their existing full-mode Markdown behavior; this issue does not promise or require a facts sidecar for those inputs.

For saved local-PDF `mode: full`, include these instructions when spawning the registered `paper-analysis` agent:

1. During the existing three-way full-text analysis, the content-analysis unit must choose author-stated future-work quotations, translations, and section names from its existing context. For saved local-PDF full mode, any body or ending section is eligible: candidate pages, keywords, and section names are reading hints, not an exclusion list. Keep each quotation continuous, semantically complete, and at most two sentences, preserving prerequisites and limitations; omit and explain an item if two sentences cannot preserve them. The model decides author intent and completeness; the helper only checks exact source evidence. Abstract-only inputs retain the abstract-ending rule, and other modes retain their existing source requirements. During synthesis, also keep a compact `facts-draft.json` containing only facts established in these same three results. Do not add a fourth analysis unit, another semantic model, or a second full-paper model reading for quotations or facts; do not regex/grep final Markdown to reconstruct facts.
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
3. Preserve the existing full-analysis Markdown quality and future-work evidence chain. Extract once with `future_work.py prepare` before Step 3; reuse its `source_pages` and `page_quality` rather than additionally running full-text extraction/quality commands. Reuse fingerprint-validated full-text OCR cache or assemble the one full-text input file from the prepared pages after necessary OCR merges. Reuse exact page OCR from this full run or the existing `pdf_runtime.py validate-ocr-cache` path bound to the same PDF and `prepare.pdf_sha256`; retain page text alongside the full reconstructed-text cache. Required candidate pages and additional actually quoted `untrusted/empty` pages may be merged with `merge-ocr`; keep required-page completeness and already-resolved page state. Only missing, needed bad pages use the existing OCR authorization path. Do not require all non-candidate bad pages to be OCRed, treat unresolved bad text as evidence, or OCR readable pages because a quotation did not match.
4. After synthesis, **write the completed Markdown to its final `<analysis>.md` path first** and confirm it exists. Only then run `future_work.py upgrade-full-sidecar --analysis "<analysis>.md" --prepared "<debug>/prepare.json"`. It reads the written analysis and this same prepared evidence locally, validates every quotation against continuous `source_pages`, and only after all pass patches the future-work section and writes `<analysis>.md.future_work.json`. It must not depend on a sibling `candidates.json`. Matching supports one page or two adjacent physical pages of the same PDF; the helper supplies the real starting page/range. Without an explicit page, repeated quotations use the first valid physical-page/offset match; explicit starting pages must match. Preserve existing valid candidate quote/ID, sidecar schema, and facts links; do not migrate old sidecars. On failure stop before facts, report incomplete even if initial Markdown remains, and never bypass validation, hand-write a sidecar, or claim no future work for the whole paper. A single quotation correction uses only necessary local text and the failure reason, never another full-paper reading.
5. Only after that future-work sidecar has `status: ok`, run:

   ```bash
   uv run "$FACTS_SCRIPT" validate --draft "<temp>/facts-draft.json"
   uv run "$FACTS_SCRIPT" finalize \
     --analysis "<analysis>.md" \
     --draft "<temp>/facts-draft.json" \
     --future-work "<analysis>.md.future_work.json" \
     --input "<source.pdf>" \
     --evidence-level fulltext
   ```

6. Treat `facts.py` as the only writer/validator of `<analysis>.md.facts.json`. It supplies schema/version and the source fingerprint, verifies that the future-work sidecar belongs to the same analysis/evidence level/PDF fingerprint, and injects exact `future_work_ids`; do not hand-write or patch that sidecar.
7. Return success for a saved local-PDF full run only after the Markdown file and both sidecars exist, with both sidecars at `status: ok`. A validation/finalization failure is an error, not a reason to silently omit a sidecar.

The executable order for the saved local-PDF full path is therefore: **prepare/extract once → reuse authorized OCR and validated caches → existing three-way model analysis once → assemble Markdown and facts draft → write Markdown → local upgrade/validate future-work sidecar → finalize facts → report success**. Additional actually quoted bad pages reuse the same authorized local merge path before upgrade; a failed run may retain its initial Markdown but must not report three-artifact success. Each file retains its existing atomic-write behavior; this is not a cross-file transaction.

This keeps `facts.json` compact enough for downstream `professor-contact` Stage 2/3 and lets callers detect staleness by `schema`, `generator_version`, and `input_fingerprint` without re-reading the PDF.

## Runtime

- Direct clone/development: run `uv sync --locked` at the repository root. The project dependency is `scholar-workflow-pdfx>=0.1.0,<0.2`, which supplies both `import pdfx` and PyMuPDF transitively.
- Normalized JSON validator: run `uv run <absolute paper_input.py> <absolute-json-path>` and use only its canonical output.
- Saved local-PDF full extraction: run `uv run <absolute future_work.py> prepare ...` once and reuse `source_pages`/`page_quality` for the full-text input and source validation. Other PDF runs retain `uv run <absolute pdf_runtime.py> extract ...`; all bad-page rendering retains `uv run <absolute pdf_runtime.py> render ...`. These PEP 723 helpers bootstrap `scholar-workflow-pdfx==0.1.0`, so APM installations do not depend on host PyMuPDF.
- Standalone future-work helper: run `uv run <absolute future_work.py> ...`; PEP 723 metadata bootstraps `scholar-workflow-pdfx==0.1.0` without requiring a synced checkout.
- Structured facts helper: run `uv run <absolute facts.py> validate ...` / `finalize ...`. It has no third-party dependencies and never invokes a model or parses the analysis Markdown for facts.
- PDF quality CLI: invoke it through the released distribution, e.g. `uvx --from "scholar-workflow-pdfx==0.1.0" pdfx quality "<PDF>" --json`. Do not assume a global `pdfx` executable.

## Boundaries

- Never infer author intent from a limitation or reader speculation.
- Never invent metadata, quotations, page numbers, citations, or structured facts.
- Never add a second full-paper model call or extra analysis unit for future-work quotations or `facts.json`.
- Never reconstruct structured facts by regex/grep over the human Markdown.
- Never claim the three-artifact contract for non-PDF full-mode inputs.
- Never run `upgrade-full-sidecar` before the final analysis Markdown exists on disk.
- Never OCR a needed bad page again when exact page OCR text from the same PDF is already available and fingerprint-validated; never OCR readable pages merely because quotation validation failed.
- Keep temporary and generated output outside the source tree unless the user explicitly selects an output directory.
- Consume the installed `scholar-workflow-pdfx` package/API only; do not depend on that distribution's layout or an APM checkout path.
- Do not import PyMuPDF from the host Python in the agent; use the uv-managed PDF runtime helper.
- Keep the existing `vision-tools` authorization and fingerprint-validated cache paths. Retain exact page text for deterministic future-work reuse, including additional actually quoted bad pages; candidate-page automatic authorization does not authorize other pages.
