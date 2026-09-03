#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pdf-processing-core @ git+https://github.com/ScholarWorkflow/pdf-processing-core.git@main",
# ]
# ///
"""Self-contained PDF extraction and page rendering helpers for paper-analysis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover - compatibility with older PyMuPDF imports
    import fitz  # type: ignore[no-redef]


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

    args = parser.parse_args()
    try:
        if args.command == "extract":
            result = extract_pdf(args.pdf, args.output)
        else:
            result = render_page(args.pdf, args.page, args.output, args.scale)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0
    except (OSError, ValueError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
