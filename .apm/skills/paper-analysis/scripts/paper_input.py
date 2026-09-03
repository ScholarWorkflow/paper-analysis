#!/usr/bin/env python3
"""Validate and read normalized paper-analysis JSON inputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_normalized_input(path: Path) -> dict[str, Any]:
    if not path.is_absolute():
        raise ValueError("normalized paper input path must be absolute")
    if not path.is_file():
        raise ValueError(f"paper input does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid paper input JSON: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("paper input JSON must be an object")
    if payload.get("schema") != 1:
        raise ValueError("paper input schema must be 1")
    if payload.get("kind") != "paper-analysis-input":
        raise ValueError("paper input kind must be paper-analysis-input")
    if payload.get("level") != "abstract":
        raise ValueError("only abstract normalized paper inputs are supported")
    abstract = payload.get("abstract")
    if not isinstance(abstract, str) or not abstract.strip():
        raise ValueError("paper input abstract must be a non-empty string")
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("paper input metadata must be an object")
    authors = metadata.get("authors")
    if authors is not None and (
        not isinstance(authors, list)
        or not all(isinstance(author, str) and author.strip() for author in authors)
    ):
        raise ValueError("paper input metadata.authors must be a list of non-empty strings")
    year = metadata.get("year")
    if year is not None and (not isinstance(year, int) or isinstance(year, bool)):
        raise ValueError("paper input metadata.year must be an integer")
    for field in ("title", "venue", "doi"):
        value = metadata.get(field)
        if value is not None and not isinstance(value, str):
            raise ValueError(f"paper input metadata.{field} must be a string")
    return {
        "schema": 1,
        "level": "abstract",
        "metadata": {
            "title": metadata.get("title"),
            "authors": authors or [],
            "year": year,
            "venue": metadata.get("venue"),
            "doi": metadata.get("doi"),
        },
        "abstract": abstract.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        result = load_normalized_input(args.path)
    except (OSError, ValueError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
