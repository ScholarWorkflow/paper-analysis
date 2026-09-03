#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pdf-processing-core @ git+https://github.com/ScholarWorkflow/pdf-processing-core.git@main",
# ]
# ///
"""Self-contained PDF extraction, rendering, and OCR-cache helpers."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover - compatibility with older PyMuPDF imports
    import fitz  # type: ignore[no-redef]


SHA256_RE = re.compile(r"[0-9a-f]{64}")


def extract_pdf(pdf_path: Path, output_path: Path) -> dict[str, object]:
    if not pdf_path.is_absolute():
        raise ValueError("PDF path must be absolute")
    if not pdf_path.is_file():
        raise ValueError(f"PDF does not exist: {pdf_path}")
    if not output_path.is_absolute():
        raise ValueError("output path must be absolute")

    document = fitz.open(pdf_path)
    try:
        pages = []
        for page_number, page in enumerate(document, start=1):
            pages.append(f"<!-- PDF_PAGE: {page_number} -->\n{page.get_text() or ''}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n\n".join(pages), encoding="utf-8")
        return {"ok": True, "pages": len(document), "output": str(output_path)}
    finally:
        document.close()


def render_page(pdf_path: Path, page_number: int, output_path: Path, scale: float) -> dict[str, object]:
    if not pdf_path.is_absolute():
        raise ValueError("PDF path must be absolute")
    if not pdf_path.is_file():
        raise ValueError(f"PDF does not exist: {pdf_path}")
    if not output_path.is_absolute():
        raise ValueError("output path must be absolute")
    if page_number < 1:
        raise ValueError("page must be >= 1")
    if scale <= 0:
        raise ValueError("scale must be > 0")

    document = fitz.open(pdf_path)
    try:
        if page_number > len(document):
            raise ValueError(f"page {page_number} exceeds PDF page count {len(document)}")
        page = document[page_number - 1]
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pixmap.save(output_path)
        return {"ok": True, "page": page_number, "output": str(output_path)}
    finally:
        document.close()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def fulltext_cache_metadata_path(cache_path: Path) -> Path:
    return Path(str(cache_path) + ".meta.json")


def validate_pages_payload(raw: Any) -> dict[str, str]:
    pages_raw = raw.get("pages") if isinstance(raw, dict) else raw
    if not isinstance(pages_raw, dict):
        raise ValueError("OCR pages JSON must be an object or contain pages")
    pages: dict[int, str] = {}
    for raw_page, text in pages_raw.items():
        try:
            page = int(raw_page)
        except (TypeError, ValueError) as error:
            raise ValueError(f"invalid OCR page: {raw_page}") from error
        if page < 1:
            raise ValueError(f"invalid OCR page: {raw_page}")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"OCR text for page {page} must be non-empty")
        pages[page] = text
    return {str(page): pages[page] for page in sorted(pages)}


def validate_fulltext_ocr_cache(
    pdf_path: Path,
    cache_path: Path,
    output_path: Path | None = None,
    expected_sha256: str | None = None,
) -> dict[str, object]:
    if not pdf_path.is_absolute():
        raise ValueError("PDF path must be absolute")
    if not pdf_path.is_file():
        raise ValueError(f"PDF does not exist: {pdf_path}")
    if not cache_path.is_absolute():
        raise ValueError("cache path must be absolute")
    if not cache_path.is_file():
        raise ValueError(f"full-text OCR cache does not exist: {cache_path}")
    if output_path is not None and not output_path.is_absolute():
        raise ValueError("output path must be absolute")
    if expected_sha256 is not None and (
        not isinstance(expected_sha256, str) or not SHA256_RE.fullmatch(expected_sha256)
    ):
        raise ValueError("expected PDF SHA256 must be 64 lowercase hex characters")

    current_sha256 = sha256_file(pdf_path)
    if expected_sha256 is not None and current_sha256 != expected_sha256:
        raise ValueError("current PDF fingerprint does not match expected PDF fingerprint")

    metadata_path = fulltext_cache_metadata_path(cache_path)
    if not metadata_path.is_file():
        raise ValueError("full-text OCR cache metadata is missing")
    metadata = read_json(metadata_path)
    if not isinstance(metadata, dict) or metadata.get("schema") != 1:
        raise ValueError("full-text OCR cache metadata must use schema 1")
    if metadata.get("pdf_sha256") != current_sha256:
        raise ValueError("full-text OCR cache fingerprint does not match current PDF fingerprint")

    text = cache_path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError("full-text OCR cache must be non-empty")
    if output_path is not None:
        atomic_write(output_path, text)
    return {
        "ok": True,
        "pdf_sha256": current_sha256,
        "cache": str(cache_path),
        "metadata": str(metadata_path),
        "output": str(output_path) if output_path is not None else None,
    }


def update_fulltext_ocr_cache(pdf_path: Path, cache_path: Path, text_path: Path) -> dict[str, object]:
    if not pdf_path.is_absolute():
        raise ValueError("PDF path must be absolute")
    if not pdf_path.is_file():
        raise ValueError(f"PDF does not exist: {pdf_path}")
    if not cache_path.is_absolute():
        raise ValueError("cache path must be absolute")
    if not text_path.is_absolute():
        raise ValueError("text path must be absolute")
    if not text_path.is_file():
        raise ValueError(f"full-text OCR source does not exist: {text_path}")

    text = text_path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError("full-text OCR source must be non-empty")
    pdf_sha256 = sha256_file(pdf_path)
    metadata_path = fulltext_cache_metadata_path(cache_path)
    # Write the text first and the fingerprint metadata last. A crash before the
    # metadata write leaves a cache that validation treats as missing/stale.
    atomic_write(cache_path, text)
    atomic_json(metadata_path, {"schema": 1, "pdf_sha256": pdf_sha256})
    return {
        "ok": True,
        "pdf_sha256": pdf_sha256,
        "cache": str(cache_path),
        "metadata": str(metadata_path),
    }


def validate_ocr_cache(
    pdf_path: Path,
    cache_path: Path,
    expected_sha256: str,
    output_path: Path | None = None,
) -> dict[str, object]:
    if not pdf_path.is_absolute():
        raise ValueError("PDF path must be absolute")
    if not pdf_path.is_file():
        raise ValueError(f"PDF does not exist: {pdf_path}")
    if not cache_path.is_absolute():
        raise ValueError("cache path must be absolute")
    if not cache_path.is_file():
        raise ValueError(f"OCR cache does not exist: {cache_path}")
    if not isinstance(expected_sha256, str) or not SHA256_RE.fullmatch(expected_sha256):
        raise ValueError("expected PDF SHA256 must be 64 lowercase hex characters")
    if output_path is not None and not output_path.is_absolute():
        raise ValueError("output path must be absolute")

    current_sha256 = sha256_file(pdf_path)
    if current_sha256 != expected_sha256:
        raise ValueError("current PDF fingerprint does not match prepared PDF fingerprint")

    raw = read_json(cache_path)
    if not isinstance(raw, dict) or raw.get("schema") != 1:
        raise ValueError("OCR cache must use schema 1")
    cache_sha256 = raw.get("pdf_sha256")
    if cache_sha256 != expected_sha256:
        raise ValueError("OCR cache fingerprint does not match current PDF fingerprint")
    pages = validate_pages_payload(raw)
    payload = {"schema": 1, "pdf_sha256": expected_sha256, "pages": pages}
    if output_path is not None:
        atomic_json(output_path, payload)
    return {
        "ok": True,
        "pdf_sha256": expected_sha256,
        "pages": len(pages),
        "output": str(output_path) if output_path is not None else None,
    }


def update_ocr_cache(pdf_path: Path, cache_path: Path, pages_path: Path) -> dict[str, object]:
    if not pdf_path.is_absolute():
        raise ValueError("PDF path must be absolute")
    if not pdf_path.is_file():
        raise ValueError(f"PDF does not exist: {pdf_path}")
    if not cache_path.is_absolute():
        raise ValueError("cache path must be absolute")
    if not pages_path.is_absolute():
        raise ValueError("pages path must be absolute")
    if not pages_path.is_file():
        raise ValueError(f"OCR pages JSON does not exist: {pages_path}")

    pdf_sha256 = sha256_file(pdf_path)
    new_pages = validate_pages_payload(read_json(pages_path))
    merged_pages: dict[str, str] = {}
    if cache_path.is_file():
        try:
            existing = read_json(cache_path)
            if (
                isinstance(existing, dict)
                and existing.get("schema") == 1
                and existing.get("pdf_sha256") == pdf_sha256
            ):
                merged_pages.update(validate_pages_payload(existing))
        except (OSError, ValueError, json.JSONDecodeError):
            # A malformed or stale cache is never reused. Fresh current-run OCR
            # replaces it under the current PDF fingerprint.
            merged_pages = {}
    merged_pages.update(new_pages)
    payload = {"schema": 1, "pdf_sha256": pdf_sha256, "pages": merged_pages}
    atomic_json(cache_path, payload)
    return {"ok": True, "pdf_sha256": pdf_sha256, "pages": len(merged_pages), "cache": str(cache_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    extract_parser = commands.add_parser("extract")
    extract_parser.add_argument("pdf", type=Path)
    extract_parser.add_argument("--output", required=True, type=Path)

    render_parser = commands.add_parser("render")
    render_parser.add_argument("pdf", type=Path)
    render_parser.add_argument("--page", required=True, type=int)
    render_parser.add_argument("--output", required=True, type=Path)
    render_parser.add_argument("--scale", type=float, default=4.0)

    fulltext_validate_parser = commands.add_parser("validate-fulltext-ocr-cache")
    fulltext_validate_parser.add_argument("--pdf", required=True, type=Path)
    fulltext_validate_parser.add_argument("--cache", required=True, type=Path)
    fulltext_validate_parser.add_argument("--output", type=Path)
    fulltext_validate_parser.add_argument("--expected-sha256")

    fulltext_update_parser = commands.add_parser("update-fulltext-ocr-cache")
    fulltext_update_parser.add_argument("--pdf", required=True, type=Path)
    fulltext_update_parser.add_argument("--cache", required=True, type=Path)
    fulltext_update_parser.add_argument("--text", required=True, type=Path)

    cache_validate_parser = commands.add_parser("validate-ocr-cache")
    cache_validate_parser.add_argument("--pdf", required=True, type=Path)
    cache_validate_parser.add_argument("--cache", required=True, type=Path)
    cache_validate_parser.add_argument("--expected-sha256", required=True)
    cache_validate_parser.add_argument("--output", type=Path)

    cache_update_parser = commands.add_parser("update-ocr-cache")
    cache_update_parser.add_argument("--pdf", required=True, type=Path)
    cache_update_parser.add_argument("--cache", required=True, type=Path)
    cache_update_parser.add_argument("--pages", required=True, type=Path)

    args = parser.parse_args()
    try:
        if args.command == "extract":
            result = extract_pdf(args.pdf, args.output)
        elif args.command == "render":
            result = render_page(args.pdf, args.page, args.output, args.scale)
        elif args.command == "validate-fulltext-ocr-cache":
            result = validate_fulltext_ocr_cache(
                args.pdf, args.cache, args.output, expected_sha256=args.expected_sha256
            )
        elif args.command == "update-fulltext-ocr-cache":
            result = update_fulltext_ocr_cache(args.pdf, args.cache, args.text)
        elif args.command == "validate-ocr-cache":
            result = validate_ocr_cache(args.pdf, args.cache, args.expected_sha256, args.output)
        else:
            result = update_ocr_cache(args.pdf, args.cache, args.pages)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
