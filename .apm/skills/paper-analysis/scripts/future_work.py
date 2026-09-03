#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pdf-processing-core @ git+https://github.com/ScholarWorkflow/pdf-processing-core.git@main",
# ]
# ///
"""Deterministic future-work evidence helper for paper-analysis.

This program intentionally only extracts, validates, and patches evidence.  It
never calls an OCR engine or a language model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover - exercised by the CLI environment
    import fitz  # type: ignore[no-redef]

from pdfx.quality import score_page


FUTURE_HEADING = "## 作者明说的未来工作（Future Work）"
LIMITATIONS_ANCHOR = "## 局限性与批判性评价"
HELP_ANCHOR = "## 对自身研究的帮助评估"
KEYWORD_RE = re.compile(
    r"(?:\b(?:future work|future research|future direction|future study|"
    r"further work|further research|in future|we will|we plan to|"
    r"remain(?:s)? to be)\b|今後の課題|今後|将来の課題|未来工作|未来研究|后续工作)",
    re.IGNORECASE,
)
TOC_RE = re.compile(
    r"future work|future research|future direction|future study|"
    r"further work|discussion|conclusion|concluding|今後の課題|今後|"
    r"結論|考察|おわりに",
    re.IGNORECASE,
)
SPACE_RE = re.compile(r"\s+")
MAX_QUOTE_CHARS = 1200


def normalized_quote(value: str) -> str:
    """Normalize only Unicode and whitespace so quote matching stays literal."""
    return SPACE_RE.sub(" ", unicodedata.normalize("NFKC", value).strip())


def match_quote(value: str) -> str:
    """Normalize harmless extraction hyphenation before matching PDF text."""
    return normalized_quote(value).replace("- ", "")


def quote_id(quote: str) -> str:
    return hashlib.sha256(normalized_quote(quote).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def atomic_json(path: Path, payload: Any) -> None:
    atomic_write(path, json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def page_candidates(text: str, page: int) -> list[dict[str, Any]]:
    """Return bounded exact source strings for semantic future-work selection."""
    candidates = []
    for paragraph in re.split(r"\n\s*\n", text):
        quote = normalized_quote(paragraph)
        # Keep sentences, rather than whole pages or table-heavy paragraphs,
        # as the only valid quote units. Split before capitalized prose too
        # because PDF extraction often drops the original separating space.
        for sentence in re.split(r"(?<=[.!?。！？])(?=\s|[A-Z])", quote):
            sentence = normalized_quote(sentence)
            if sentence and len(sentence) <= MAX_QUOTE_CHARS:
                candidates.append({"id": quote_id(sentence), "quote": sentence, "page": page})
    return candidates


def render_candidates(payload: dict[str, Any]) -> str:
    """Create the bounded, page-marked input consumed by the gap-only agent."""
    chunks = []
    for candidate in payload["candidates"]:
        chunks.extend([
            f"<!-- PDF_PAGE: {candidate['page']} -->",
            candidate["quote"],
            "",
        ])
    return "\n".join(chunks).rstrip() + "\n"


def refresh_candidates(payload: dict[str, Any], pages: dict[int, str]) -> dict[str, Any]:
    """Replace only preselected page text after the agent OCRs those pages."""
    selected_pages = set(payload["selection"]["pages"])
    candidates = []
    for page in sorted(selected_pages):
        page_text = pages.get(page)
        if page_text is None:
            candidates.extend(item for item in payload["candidates"] if item["page"] == page)
        else:
            candidates.extend(page_candidates(page_text, page))
    unique = {candidate["id"]: candidate for candidate in candidates}
    updated = dict(payload)
    updated["candidates"] = list(unique.values())
    updated["ocr_required_pages"] = [page for page in payload["ocr_required_pages"] if page not in pages]
    updated["ocr_resolved_pages"] = sorted(pages)
    return updated


def toc_candidate_pages(toc: list[dict[str, Any]], page_count: int) -> set[int]:
    """Return each matching outline entry's page range, stopping at its peer."""
    pages = set()
    for index, entry in enumerate(toc):
        if not TOC_RE.search(entry["title"]):
            continue
        end = page_count
        level = entry["level"]
        for sibling in toc[index + 1:]:
            if sibling["level"] <= level:
                end = sibling["page"] - 1
                break
        pages.update(range(entry["page"], max(entry["page"], end) + 1))
    return pages


def prepare(pdf_path: Path, last_pages: int) -> dict[str, Any]:
    if not pdf_path.is_file():
        raise ValueError(f"PDF does not exist: {pdf_path}")
    digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    document = fitz.open(pdf_path)
    try:
        page_count = len(document)
        toc = [{"level": level, "title": title, "page": page} for level, title, page, *_ in document.get_toc(simple=False)]
        trailing_pages = set(range(max(1, page_count - last_pages + 1), page_count + 1))
        qualities = []
        extracted_pages = []
        keyword_pages = set()
        for index, page in enumerate(document, start=1):
            text = page.get_text() or ""
            extracted_pages.append({"page": index, "text": text})
            quality = score_page(page, index).to_dict()
            qualities.append(quality)
            if KEYWORD_RE.search(text):
                keyword_pages.add(index)
        toc_pages = toc_candidate_pages(toc, page_count)
        selected_pages = sorted(trailing_pages | toc_pages | keyword_pages)
        candidates = []
        for page_data in extracted_pages:
            if page_data["page"] in selected_pages:
                candidates.extend(page_candidates(page_data["text"], page_data["page"]))
        # A single paragraph may include repeated text through page headers.
        unique = {candidate["id"]: candidate for candidate in candidates}
        return {
            "schema": 1,
            "pdf": pdf_path.name,
            "pdf_sha256": digest,
            "page_count": page_count,
            "toc": toc,
            "selection": {
                "keywords": KEYWORD_RE.pattern,
                "last_pages": last_pages,
                "toc_pages": sorted(toc_pages),
                "keyword_pages": sorted(keyword_pages),
                "pages": selected_pages,
            },
            "page_quality": qualities,
            "ocr_required_pages": [
                quality["page"] for quality in qualities
                if quality["page"] in selected_pages and quality["tier"] in {"untrusted", "empty"}
            ],
            "candidates": list(unique.values()),
        }
    finally:
        document.close()


def prepare_summary(payload: dict[str, Any]) -> dict[str, Any]:
    tiers: dict[str, int] = {}
    for page in payload["page_quality"]:
        tiers[page["tier"]] = tiers.get(page["tier"], 0) + 1
    return {
        "result": "ok",
        "pdf": payload["pdf"],
        "pdf_sha256": payload["pdf_sha256"],
        "page_count": payload["page_count"],
        "toc_matches": payload["selection"]["toc_pages"],
        "keyword_matches": payload["selection"]["keyword_pages"],
        "candidate_pages": payload["selection"]["pages"],
        "candidate_count": len(payload["candidates"]),
        "ocr_required_pages": payload["ocr_required_pages"],
        "quality": tiers,
    }


def load_candidates(path: Path) -> list[dict[str, Any]]:
    payload = read_json(path)
    if isinstance(payload, dict):
        candidates = payload.get("candidates")
    else:
        candidates = payload
    if not isinstance(candidates, list):
        raise ValueError("candidates JSON must be a list or an object with candidates")
    return candidates


def merge_ocr(prepared_path: Path, ocr_path: Path, debug_dir: Path | None) -> dict[str, Any]:
    prepared = read_json(prepared_path)
    raw = read_json(ocr_path)
    pages_raw = raw.get("pages") if isinstance(raw, dict) else raw
    if not isinstance(pages_raw, dict):
        raise ValueError("OCR JSON must be an object or contain pages")
    pages = {}
    for raw_page, text in pages_raw.items():
        try:
            page = int(raw_page)
        except (TypeError, ValueError) as error:
            raise ValueError(f"invalid OCR page: {raw_page}") from error
        if page not in prepared["ocr_required_pages"]:
            raise ValueError(f"OCR page {page} was not required by prepare")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"OCR text for page {page} must be non-empty")
        pages[page] = text
    if set(pages) != set(prepared["ocr_required_pages"]):
        raise ValueError("OCR JSON must contain every required candidate page")
    result = refresh_candidates(prepared, pages)
    if debug_dir:
        atomic_json(debug_dir / "prepare.json", result)
        atomic_json(debug_dir / "candidates.json", {"candidates": result["candidates"]})
        atomic_write(debug_dir / "candidates.md", render_candidates(result))
    return result


def validate_items(items: Any, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(items, dict):
        items = items.get("items")
    if not isinstance(items, list):
        raise ValueError("items JSON must be a list or an object with items")
    candidate_locations = {
        (normalized_quote(str(item.get("quote", ""))), item.get("page"))
        for item in candidates if isinstance(item, dict)
    }
    validated = []
    seen_ids = set()
    for number, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"items[{number}] must be an object")
        allowed = {"id", "quote", "translation_zh", "source", "page"}
        unknown = set(item) - allowed
        if unknown:
            raise ValueError(f"items[{number}] has unknown fields: {', '.join(sorted(unknown))}")
        missing = [field for field in ("quote", "translation_zh", "source", "page") if field not in item]
        if missing:
            raise ValueError(f"items[{number}] missing fields: {', '.join(missing)}")
        if not all(isinstance(item[field], str) and item[field].strip() for field in ("quote", "translation_zh", "source")):
            raise ValueError(f"items[{number}] quote, translation_zh, and source must be non-empty strings")
        if len(item["quote"]) > MAX_QUOTE_CHARS:
            raise ValueError(f"items[{number}].quote exceeds {MAX_QUOTE_CHARS} characters")
        if not isinstance(item["page"], int) or isinstance(item["page"], bool) or item["page"] < 1:
            raise ValueError(f"items[{number}].page must be a positive integer")
        quote = normalized_quote(item["quote"])
        if (quote, item["page"]) not in candidate_locations:
            raise ValueError(f"items[{number}].quote and page are not an exact prepared candidate")
        identifier = item.get("id") or quote_id(quote)
        if not isinstance(identifier, str) or not re.fullmatch(r"[0-9a-f]{64}", identifier):
            raise ValueError(f"items[{number}].id must be a SHA256 hex string")
        if identifier != quote_id(quote):
            raise ValueError(f"items[{number}].id does not match normalized quote SHA256")
        if identifier in seen_ids:
            raise ValueError(f"items[{number}].id is duplicated")
        seen_ids.add(identifier)
        validated.append({"id": identifier, "quote": quote, "translation_zh": item["translation_zh"].strip(), "source": item["source"].strip(), "page": item["page"]})
    return validated


def render_section(items: list[dict[str, Any]]) -> str:
    if not items:
        return FUTURE_HEADING + "\n—（论文未明示 future work）\n"
    lines = [FUTURE_HEADING]
    for item in items:
        lines.extend([f"- 原文：{item['quote']}", f"  译：{item['translation_zh']}", f"  出处：{item['source']}（p.{item['page']}）"])
    return "\n".join(lines) + "\n"


def patch_analysis(analysis: Path, items: list[dict[str, Any]]) -> None:
    if not analysis.is_file():
        raise ValueError(f"analysis does not exist: {analysis}")
    text = analysis.read_text(encoding="utf-8")
    left = text.find(LIMITATIONS_ANCHOR)
    right = text.find(HELP_ANCHOR)
    if left < 0 or right < 0 or left >= right:
        raise ValueError("analysis must contain exact ordered template anchors")
    middle_start = text.find("\n", left) + 1
    future = text.find(FUTURE_HEADING, middle_start, right)
    section = render_section(items)
    if future >= 0:
        next_heading = re.search(r"^##\s", text[future + len(FUTURE_HEADING):right], re.MULTILINE)
        replacement_end = future + len(FUTURE_HEADING) + next_heading.start() if next_heading else right
        updated = text[:future] + section + text[replacement_end:]
    else:
        separator = "" if text[middle_start:right].endswith("\n\n") else "\n"
        updated = text[:right] + separator + section + text[right:]
    atomic_write(analysis, updated)


def sidecar_path(analysis: Path) -> Path:
    return Path(str(analysis) + ".future_work.json")


def finalize(
    analysis: Path,
    items_path: Path,
    candidates_path: Path,
    patch: bool,
    pdf_sha256: str | None = None,
    evidence_level: str = "fulltext",
    extractor_version: str = "future-work-v1",
) -> dict[str, Any]:
    items = validate_items(read_json(items_path), load_candidates(candidates_path))
    payload = {
        "schema": 1,
        "extractor_version": extractor_version,
        "analysis": analysis.name,
        "source_pdf_fingerprint": f"sha256:{pdf_sha256}" if pdf_sha256 else None,
        "evidence_level": evidence_level,
        "status": "ok",
        "items": items,
    }
    if patch:
        patch_analysis(analysis, items)
    atomic_json(sidecar_path(analysis), payload)
    return {"ok": True, "sidecar": str(sidecar_path(analysis)), "items": len(items), "patched": patch}


def upgrade_full_sidecar(
    analysis: Path, prepared_path: Path,
) -> dict[str, Any]:
    """Upgrade a freshly written full-analysis section using prepared PDF pages."""
    if not analysis.is_file():
        raise ValueError(f"analysis does not exist: {analysis}")
    prepared = read_json(prepared_path)
    if not isinstance(prepared, dict) or not isinstance(prepared.get("pdf_sha256"), str):
        raise ValueError("prepared JSON must contain pdf_sha256")
    text = analysis.read_text(encoding="utf-8")
    match = re.search(r"^" + re.escape(FUTURE_HEADING) + r"\s*$\n(.*?)(?=^##\s|\Z)", text, re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError("analysis has no future-work section")
    items_from_analysis = []
    current = {}
    for line in match.group(1).splitlines():
        if line.startswith("- 原文："):
            if current:
                items_from_analysis.append(current)
            current = {"quote": line.removeprefix("- 原文：").strip()}
        elif line.startswith("  译："):
            current["translation_zh"] = line.removeprefix("  译：").strip()
        elif line.startswith("  出处："):
            source = line.removeprefix("  出处：").strip()
            current["source"] = re.sub(r"（p\.\d+）$", "", source).strip()
    if current:
        items_from_analysis.append(current)
    by_quote = {match_quote(item["quote"]): item for item in load_candidates(prepared_path)}
    items = []
    for number, item in enumerate(items_from_analysis, start=1):
        candidate = by_quote.get(match_quote(item.get("quote", "")))
        if not candidate:
            raise ValueError(f"full future-work item {number} is not an exact prepared candidate")
        if not all(item.get(field) for field in ("quote", "translation_zh", "source")):
            raise ValueError(f"full future-work item {number} is incomplete")
        items.append({
            "id": candidate["id"],
            "quote": candidate["quote"],
            "translation_zh": item["translation_zh"],
            "source": item["source"],
            "page": candidate["page"],
        })
    items_path = analysis.parent / f".{analysis.name}.future_work_items.json"
    candidates_path = prepared_path.parent / "candidates.json"
    atomic_json(items_path, {"items": items})
    try:
        return finalize(
            analysis, items_path, candidates_path, patch=True,
            pdf_sha256=prepared["pdf_sha256"],
        )
    finally:
        try:
            items_path.unlink()
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = subcommands.add_parser("prepare")
    prepare_parser.add_argument("pdf", type=Path)
    prepare_parser.add_argument("--last-pages", type=int, default=3)
    prepare_parser.add_argument("--debug-dir", type=Path)
    validate_parser = subcommands.add_parser("validate")
    validate_parser.add_argument("--items", required=True, type=Path)
    validate_parser.add_argument("--candidates", required=True, type=Path)
    finalize_parser = subcommands.add_parser("finalize")
    finalize_parser.add_argument("--analysis", required=True, type=Path)
    finalize_parser.add_argument("--items", required=True, type=Path)
    finalize_parser.add_argument("--candidates", required=True, type=Path)
    finalize_parser.add_argument("--patch", action="store_true")
    finalize_parser.add_argument("--pdf-sha256")
    finalize_parser.add_argument("--evidence-level", default="fulltext", choices=("fulltext", "abstract_only"))
    finalize_parser.add_argument("--extractor-version", default="future-work-v1")
    merge_parser = subcommands.add_parser("merge-ocr")
    merge_parser.add_argument("--prepared", required=True, type=Path)
    merge_parser.add_argument("--ocr", required=True, type=Path)
    merge_parser.add_argument("--debug-dir", type=Path)
    upgrade_parser = subcommands.add_parser("upgrade-full-sidecar")
    upgrade_parser.add_argument("--analysis", required=True, type=Path)
    upgrade_parser.add_argument("--prepared", required=True, type=Path)
    args = parser.parse_args()
    output: dict[str, Any] = {}
    try:
        if args.command == "prepare":
            if args.last_pages < 0:
                raise ValueError("--last-pages must be non-negative")
            result = prepare(args.pdf, args.last_pages)
            if args.debug_dir:
                atomic_json(args.debug_dir / "prepare.json", result)
                atomic_json(args.debug_dir / "candidates.json", {"candidates": result["candidates"]})
                atomic_write(args.debug_dir / "candidates.md", render_candidates(result))
            output = prepare_summary(result)
        elif args.command == "validate":
            output = {"ok": True, "items": validate_items(read_json(args.items), load_candidates(args.candidates))}
        elif args.command == "finalize":
            output = finalize(
                args.analysis, args.items, args.candidates, args.patch,
                pdf_sha256=args.pdf_sha256,
                evidence_level=args.evidence_level, extractor_version=args.extractor_version,
            )
        elif args.command == "merge-ocr":
            output = merge_ocr(args.prepared, args.ocr, args.debug_dir)
        elif args.command == "upgrade-full-sidecar":
            output = upgrade_full_sidecar(args.analysis, args.prepared)
        print(json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, separators=(",", ":")), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())