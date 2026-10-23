#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "scholar-workflow-pdfx==0.1.0",
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
        # Keep bounded single-sentence hints for reading and the legacy
        # candidates-only interface. Source-backed validation accepts complete
        # continuous quotes independently of these hints. Split before capitalized prose too
        # because PDF extraction often drops the original separating space.
        # Japanese prose can follow either 。 or an ASCII full stop directly;
        # the sentence-internal abbreviation i.e. must keep its explanation.
        for sentence in re.split(
            r"(?<=。)|(?<!\bi\.e\.)(?<=[.!?！？])(?=\s|[A-Z\u3040-\u30ff\u3400-\u9fff])",
            quote,
        ):
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


def unique_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the first retained occurrence, including its original page."""
    seen = set()
    result = []
    for candidate in candidates:
        if candidate["id"] not in seen:
            seen.add(candidate["id"])
            result.append(candidate)
    return result


def source_layout(page: Any, text: str) -> list[dict[str, Any]]:
    """Map complete layout blocks to the unmodified extraction string.

    An uncertain mapping stays in the text. Geometry is used only to prove
    independent outer blocks; it never determines reading order.
    """
    blocks = []
    cursor = 0
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        lines = []
        for line in block["lines"]:
            value = "".join(span["text"] for span in line["spans"])
            if not value:
                continue
            start = text.find(value, cursor)
            if start < 0 or text[cursor:start].strip():
                return []
            end = start + len(value)
            if text[end:end + 1] == "\n":
                end += 1
            lines.append({"text": value, "start": start, "end": end,
                          "height": line["bbox"][3] - line["bbox"][1]})
            cursor = end
        if lines:
            x0, y0, x1, y1 = block["bbox"]
            edge = "top" if y1 <= page.rect.height * 0.08 else (
                "bottom" if y0 >= page.rect.height * 0.92 else None)
            blocks.append({"lines": lines, "bbox": [x0, y0, x1, y1], "edge": edge})
    if text[cursor:].strip():
        return []
    return blocks


def mark_edge_exclusions(
    source_pages: list[dict[str, Any]], layouts: list[list[dict[str, Any]]],
) -> None:
    """Record only independently justified outer headers and footers."""
    repeated: dict[tuple[str, str], set[int]] = {}
    for source, blocks in zip(source_pages, layouts):
        for block in blocks:
            if block["edge"]:
                for line in block["lines"]:
                    repeated.setdefault((block["edge"], line["text"]), set()).add(source["page"])
    for source, blocks in zip(source_pages, layouts):
        # Extraction order can put a visual header after the footer. Only
        # contiguous text-edge runs are candidates; never remove internal blocks.
        outer_indices = set()
        for indices in (range(len(blocks)), reversed(range(len(blocks)))):
            for index in indices:
                block = blocks[index]
                if not block["edge"] or not all(
                    line["text"].strip().isdecimal()
                    or len(repeated.get((block["edge"], line["text"]), set())) >= 2
                    for line in block["lines"]
                ):
                    break
                outer_indices.add(index)
        proven = set()
        for edge in ("top", "bottom"):
            indices = {index for index in outer_indices if blocks[index]["edge"] == edge}
            outer = [blocks[index] for index in indices]
            body = [block for index, block in enumerate(blocks) if index not in indices]
            if not outer or not body:
                continue
            # Keep the existing geometric separation proof, independent of
            # the position of these blocks in the extraction sequence.
            height = max(line["height"] for block in outer for line in block["lines"])
            gap = (min(block["bbox"][1] for block in body)
                   - max(block["bbox"][3] for block in outer)) if edge == "top" else (
                       min(block["bbox"][1] for block in outer)
                       - max(block["bbox"][3] for block in body))
            if gap >= height:
                proven.update(indices)
        exclusions = []
        retained = set()
        for indices in (range(len(blocks)), reversed(range(len(blocks)))):
            for index in indices:
                if index not in proven:
                    break
                retained.add(index)
        for index in sorted(retained):
            block = blocks[index]
            # source_layout permits only whitespace between mapped blocks;
            # include that gap so adjacent exclusions form a continuous run.
            start = 0 if index == 0 else blocks[index - 1]["lines"][-1]["end"]
            end = len(source["text"]) if index == len(blocks) - 1 else block["lines"][-1]["end"]
            exclusions.append({"start": start, "end": end, "text": source["text"][start:end],
                               "edge": block["edge"], "reason": "independent outer edge block"})
        source["edge_exclusions"] = exclusions


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
    updated = dict(payload)
    updated["candidates"] = unique_candidates(candidates)
    updated["ocr_required_pages"] = [page for page in payload["ocr_required_pages"] if page not in pages]
    updated["ocr_resolved_pages"] = sorted(set(payload.get("ocr_resolved_pages", [])) | set(pages))
    if "source_pages" in payload:
        updated["source_pages"] = [
            dict(source, text=pages[source["page"]], edge_exclusions=[], ocr_resolved=True)
            if source["page"] in pages else source
            for source in payload["source_pages"]
        ]
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
        layouts = []
        keyword_pages = set()
        for index, page in enumerate(document, start=1):
            text = page.get_text() or ""
            extracted_pages.append({"page": index, "text": text})
            layouts.append(source_layout(page, text))
            quality = score_page(page, index).to_dict()
            qualities.append(quality)
            if KEYWORD_RE.search(text):
                keyword_pages.add(index)
        toc_pages = toc_candidate_pages(toc, page_count)
        selected_pages = sorted(trailing_pages | toc_pages | keyword_pages)
        mark_edge_exclusions(extracted_pages, layouts)
        candidates = []
        for page_data in extracted_pages:
            if page_data["page"] in selected_pages:
                candidates.extend(page_candidates(page_data["text"], page_data["page"]))
        # A single paragraph may include repeated text through page headers.
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
            "source_pages": extracted_pages,
            "ocr_required_pages": [
                quality["page"] for quality in qualities
                if quality["page"] in selected_pages and quality["tier"] in {"untrusted", "empty"}
            ],
            "candidates": unique_candidates(candidates),
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


def load_evidence(path: Path) -> Any:
    payload = read_json(path)
    if isinstance(payload, dict) and "source_pages" in payload:
        return payload
    return payload.get("candidates") if isinstance(payload, dict) else payload


def comparison_view(
    pieces: list[tuple[int, str, int]], dehyphenate: bool,
) -> tuple[str, list[tuple[int, int, int]]]:
    """Build a comparison string with a source interval for every character.

    A piece is (physical page, original text slice, original start offset).
    Normalization keeps exact original locations, including composed Unicode.
    """
    characters = []
    for index, (page, text, start) in enumerate(pieces):
        if index:
            characters.append(("\n", (-1, 0, 0)))
        characters.extend((character, (page, offset, offset + 1))
                          for offset, character in enumerate(text, start=start))
    if dehyphenate:
        retained = []
        index = 0
        while index < len(characters):
            character, location = characters[index]
            following = index + 1
            if character == "-":
                while following < len(characters) and characters[following][0].isspace():
                    following += 1
            if (character == "-" and index > 0 and characters[index - 1][0].isalpha()
                    and following < len(characters) and characters[following][0].isalpha()
                    and any(char in "\r\n" for char, _ in characters[index + 1:following])):
                index = following
                continue
            retained.append((character, location))
            index += 1
        characters = retained
    # NFKC = NFC after compatibility decomposition. Keep a whole combining
    # cluster mapped to its original extent instead of guessing offsets after
    # Unicode composition or ligature expansion.
    clusters: list[list[tuple[str, tuple[int, int, int]]]] = []
    for character, location in characters:
        for decomposed in unicodedata.normalize("NFKD", character):
            if clusters and (unicodedata.combining(decomposed) or
                    unicodedata.normalize("NFC", "".join(char for char, _ in clusters[-1]) + decomposed)
                    != unicodedata.normalize("NFC", "".join(char for char, _ in clusters[-1])) + decomposed):
                clusters[-1].append((decomposed, location))
            else:
                clusters.append([(decomposed, location)])
    result = []
    mapping = []
    for cluster in clusters:
        value = unicodedata.normalize("NFC", "".join(char for char, _ in cluster))
        locations = [location for _, location in cluster]
        location = (locations[0][0], min(item[1] for item in locations), max(item[2] for item in locations))
        for character in value:
            if character.isspace():
                if result and result[-1] != " ":
                    result.append(" ")
                    mapping.append(location)
            else:
                result.append(character)
                mapping.append(location)
    if result and result[-1] == " ":
        result.pop()
        mapping.pop()
    return "".join(result), mapping


def source_bounds(source: dict[str, Any]) -> tuple[int, int]:
    """Trim prepared outer exclusions only when joining adjacent pages."""
    text = source["text"]
    start, end = 0, len(text)
    intervals = sorted(source.get("edge_exclusions", []), key=lambda item: item["start"])
    for interval in intervals:
        left, right = interval["start"], interval["end"]
        if (not (0 <= left <= right <= len(text))
                or interval.get("text") != text[left:right]
                or interval.get("edge") not in {"top", "bottom"}):
            raise ValueError(f"invalid edge exclusion on page {source['page']}")
    # Top/bottom describe geometry, not extraction order. Consume contiguous
    # prefix/suffix intervals only, leaving exactly one untouched body slice.
    remaining = []
    for interval in intervals:
        if interval["start"] == start:
            start = interval["end"]
        else:
            remaining.append(interval)
    for interval in reversed(remaining):
        if interval["end"] != end or interval["start"] < start:
            raise ValueError(f"non-outer edge exclusion on page {source['page']}")
        end = interval["start"]
    return start, end


class SourceLocator:
    """Find literal, quality-qualified spans in one page or one page seam."""

    def __init__(self, prepared: dict[str, Any]):
        pages = prepared.get("source_pages")
        if not isinstance(pages, list) or not all(
            isinstance(page, dict) and isinstance(page.get("page"), int)
            and not isinstance(page["page"], bool) and page["page"] > 0
            and isinstance(page.get("text"), str) for page in pages
        ):
            raise ValueError("prepared source_pages must contain page/text objects")
        self.pages = sorted(pages, key=lambda page: page["page"])
        if len({page["page"] for page in pages}) != len(pages):
            raise ValueError("prepared source_pages contains duplicate pages")
        quality = {item["page"]: item.get("tier") for item in prepared.get("page_quality", [])}
        resolved = set(prepared.get("ocr_resolved_pages", []))
        self.bad_pages = {page["page"] for page in pages
                          if (page["page"] not in resolved
                              and quality.get(page["page"]) in {None, "untrusted", "empty"})
                          or not page["text"].strip()}
        self.views: list[tuple[set[int], str, list[tuple[int, int, int]]]] = []
        for index, source in enumerate(self.pages):
            number, text = source["page"], source["text"]
            pieces = [(number, text, 0)]
            for dehyphenate in (False, True):
                value, mapping = comparison_view(pieces, dehyphenate)
                self.views.append(({number}, value, mapping))
            if index + 1 < len(self.pages) and self.pages[index + 1]["page"] == number + 1:
                following = self.pages[index + 1]
                left_start, left_end = source_bounds(source)
                right_start, right_end = source_bounds(following)
                pieces = [(number, text[left_start:left_end], left_start),
                          (number + 1, following["text"][right_start:right_end], right_start)]
                for dehyphenate in (False, True):
                    value, mapping = comparison_view(pieces, dehyphenate)
                    self.views.append(({number, number + 1}, value, mapping))

    def locate(self, quote: str, page: int | None = None) -> tuple[int, int, int, int]:
        needle = normalized_quote(quote)
        matches = []
        blocked = set()
        for pages, value, mapping in self.views:
            if page is not None and min(pages) != page:
                continue
            offset = value.find(needle)
            while offset >= 0:
                end = offset + len(needle)
                # Do not cut a single source character's Unicode expansion.
                if ((offset and mapping[offset] == mapping[offset - 1])
                        or (end < len(mapping) and mapping[end - 1] == mapping[end])):
                    offset = value.find(needle, offset + 1)
                    continue
                locations = [mapping[index] for index in range(offset, offset + len(needle))
                             if not value[index].isspace() and mapping[index][0] != -1]
                contributing = {location[0] for location in locations}
                # A joined view is valid only if the quote uses both pages.
                if locations and contributing == pages:
                    if contributing & self.bad_pages:
                        blocked.update(contributing & self.bad_pages)
                    else:
                        matches.append((locations[0][0], locations[0][1],
                                        locations[-1][0], locations[-1][2]))
                offset = value.find(needle, offset + 1)
        if matches:
            return min(matches)
        if blocked:
            raise ValueError("source text requires OCR on page(s) " + ", ".join(map(str, sorted(blocked))))
        raise ValueError("quote and page do not match continuous prepared source text")


def located_source(source: str, span: tuple[int, int, int, int]) -> str:
    # The model supplies a section name; physical page annotations come only
    # from the verified position. Remove an old trailing page/range first.
    section = re.sub(r"\s*[（(]\s*pp?\.\s*\d+(?:\s*[–—-]\s*\d+)?\s*[）)]\s*$", "", source).strip()
    return f"{section} (pp.{span[0]}–{span[2]})" if span[0] != span[2] else section


def merge_ocr(prepared_path: Path, ocr_path: Path, debug_dir: Path | None) -> dict[str, Any]:
    prepared = read_json(prepared_path)
    raw = read_json(ocr_path)
    pages_raw = raw.get("pages") if isinstance(raw, dict) else raw
    if not isinstance(pages_raw, dict):
        raise ValueError("OCR JSON must be an object or contain pages")
    if isinstance(raw, dict) and "pdf_sha256" in raw and raw["pdf_sha256"] != prepared.get("pdf_sha256"):
        raise ValueError("OCR PDF fingerprint does not match prepared PDF fingerprint")
    required = set(prepared["ocr_required_pages"])
    bad_pages = {item["page"] for item in prepared.get("page_quality", [])
                 if item.get("tier") in {"untrusted", "empty"}}
    pages = {}
    for raw_page, text in pages_raw.items():
        try:
            page = int(raw_page)
        except (TypeError, ValueError) as error:
            raise ValueError(f"invalid OCR page: {raw_page}") from error
        if page not in required | bad_pages:
            raise ValueError(f"OCR page {page} was not required or a low-quality prepared page")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"OCR text for page {page} must be non-empty")
        pages[page] = text
    if not required.issubset(pages):
        raise ValueError("OCR JSON must contain every required candidate page")
    result = refresh_candidates(prepared, pages)
    if debug_dir:
        atomic_json(debug_dir / "prepare.json", result)
        atomic_json(debug_dir / "candidates.json", {"candidates": result["candidates"]})
        atomic_write(debug_dir / "candidates.md", render_candidates(result))
    return result


def validate_items(
    items: Any, candidates: Any, *, allow_missing_page: bool = False,
) -> list[dict[str, Any]]:
    if isinstance(items, dict):
        items = items.get("items")
    if not isinstance(items, list):
        raise ValueError("items JSON must be a list or an object with items")
    prepared = candidates if isinstance(candidates, dict) and "source_pages" in candidates else None
    locator = SourceLocator(prepared) if prepared is not None else None
    if isinstance(candidates, dict):
        candidates = candidates.get("candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("candidates JSON must be a list or an object with candidates")
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
        required_fields = ("quote", "translation_zh", "source") if allow_missing_page else (
            "quote", "translation_zh", "source", "page")
        missing = [field for field in required_fields if field not in item]
        if missing:
            raise ValueError(f"items[{number}] missing fields: {', '.join(missing)}")
        if not all(isinstance(item[field], str) and item[field].strip() for field in ("quote", "translation_zh", "source")):
            raise ValueError(f"items[{number}] quote, translation_zh, and source must be non-empty strings")
        if len(item["quote"]) > MAX_QUOTE_CHARS:
            raise ValueError(f"items[{number}].quote exceeds {MAX_QUOTE_CHARS} characters")
        page = item.get("page")
        if ("page" in item and (not isinstance(page, int) or isinstance(page, bool) or page < 1)):
            raise ValueError(f"items[{number}].page must be a positive integer")
        quote = normalized_quote(item["quote"])
        source = item["source"].strip()
        if locator:
            try:
                span = locator.locate(quote, page)
            except ValueError as error:
                raise ValueError(f"items[{number}]: {error}") from error
            page = span[0]
            source = located_source(source, span)
            # Preserve a legacy candidate only when it proves the very same
            # original span. Candidate order is stable, never keyword-ranked.
            for candidate in candidates:
                if not isinstance(candidate, dict) or candidate.get("page") != page:
                    continue
                candidate_quote = candidate.get("quote")
                if not isinstance(candidate_quote, str) or not candidate_quote.strip():
                    continue
                try:
                    candidate_span = locator.locate(candidate_quote, page)
                except ValueError:
                    continue
                if candidate_span == span:
                    quote = normalized_quote(candidate_quote)
                    break
        elif allow_missing_page:
            # Old candidates-only preparations retain their original single
            # candidate matching contract; they cannot gain page-span support.
            candidate = next((candidate for candidate in candidates
                              if isinstance(candidate, dict)
                              and (page is None or candidate.get("page") == page)
                              and match_quote(str(candidate.get("quote", ""))) == match_quote(quote)), None)
            if candidate is None:
                raise ValueError(f"items[{number}].quote and page are not an exact prepared candidate")
            quote = normalized_quote(candidate["quote"])
            page = candidate["page"]
            source = located_source(source, (page, 0, page, 0))
        elif (quote, page) not in candidate_locations:
            raise ValueError(f"items[{number}].quote and page are not an exact prepared candidate")
        identifier = item.get("id") or quote_id(quote)
        if not isinstance(identifier, str) or not re.fullmatch(r"[0-9a-f]{64}", identifier):
            raise ValueError(f"items[{number}].id must be a SHA256 hex string")
        if identifier != quote_id(quote):
            raise ValueError(f"items[{number}].id does not match normalized quote SHA256")
        if identifier in seen_ids:
            raise ValueError(f"items[{number}].id is duplicated")
        seen_ids.add(identifier)
        validated.append({"id": identifier, "quote": quote, "translation_zh": item["translation_zh"].strip(), "source": source, "page": page})
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
    evidence = load_evidence(candidates_path)
    if isinstance(evidence, dict) and "source_pages" in evidence:
        prepared_digest = evidence.get("pdf_sha256")
        if not isinstance(prepared_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", prepared_digest):
            raise ValueError("prepared JSON must contain a SHA256 pdf_sha256")
        if pdf_sha256 is not None and pdf_sha256 != prepared_digest:
            raise ValueError("PDF fingerprint does not match prepared PDF fingerprint")
        pdf_sha256 = prepared_digest
    items = validate_items(read_json(items_path), evidence)
    return write_finalized(analysis, items, patch, pdf_sha256, evidence_level, extractor_version)


def write_finalized(
    analysis: Path, items: list[dict[str, Any]], patch: bool,
    pdf_sha256: str | None, evidence_level: str = "fulltext",
    extractor_version: str = "future-work-v1",
) -> dict[str, Any]:
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
    if (not isinstance(prepared, dict) or not isinstance(prepared.get("pdf_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", prepared["pdf_sha256"])):
        raise ValueError("prepared JSON must contain a SHA256 pdf_sha256")
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
            # An explicit single starting physical page remains binding.
            # Ranges are model annotations and are replaced by located pages.
            explicit_page = re.search(r"[（(]\s*p\.\s*(\d+)\s*[）)]\s*$", source)
            if explicit_page:
                current["page"] = int(explicit_page.group(1))
            current["source"] = source
    if current:
        items_from_analysis.append(current)
    items = validate_items(items_from_analysis, prepared, allow_missing_page=True)
    return write_finalized(analysis, items, True, prepared["pdf_sha256"])


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
            output = {"ok": True, "items": validate_items(read_json(args.items), load_evidence(args.candidates))}
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
