#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Validate and finalize compact structured facts from a full paper-analysis pass.

The model-facing coordinator writes a small draft while it is already synthesizing
its full-text analysis. This helper never reads the human Markdown for facts and
never invokes a model. It validates the draft, fingerprints the original/canonical
input, joins only validated future-work IDs from the same analysis/source, and
atomically writes the sidecar.
"""

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

SCHEMA = 1
KIND = "paper-analysis-facts"
GENERATOR_VERSION = "facts-v1"
MAX_TEXT = 1600
MAX_LIST_ITEMS = 24
MAX_TOPIC_TERMS = 32
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"input does not exist: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string or null")
    text = value.strip()
    if not text:
        return None
    if len(text) > MAX_TEXT:
        raise ValueError(f"{field} exceeds {MAX_TEXT} characters")
    return text


def clean_required_text(value: Any, field: str) -> str:
    text = clean_optional_text(value, field)
    if text is None:
        raise ValueError(f"{field} must be a non-empty string")
    return text


def clean_text_list(value: Any, field: str, *, maximum: int = MAX_LIST_ITEMS) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    if len(value) > maximum:
        raise ValueError(f"{field} has more than {maximum} items")
    cleaned: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        text = clean_required_text(item, f"{field}[{index}]")
        if text not in seen:
            seen.add(text)
            cleaned.append(text)
    return cleaned


def clean_anchors(value: Any) -> dict[str, list[str]]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("source_anchors must be an object")
    allowed = {"research_problem", "research_object", "approach", "findings", "contributions", "limitations"}
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"source_anchors has unknown fields: {', '.join(sorted(unknown))}")
    return {
        key: clean_text_list(items, f"source_anchors.{key}", maximum=12)
        for key, items in value.items()
    }


def validate_paper(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("paper must be an object")
    allowed = {"title", "authors", "year", "venue", "doi"}
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"paper has unknown fields: {', '.join(sorted(unknown))}")
    title = clean_required_text(value.get("title"), "paper.title")
    authors = clean_text_list(value.get("authors", []), "paper.authors", maximum=32)
    year = value.get("year")
    if year is not None and (not isinstance(year, int) or isinstance(year, bool) or year < 1000 or year > 9999):
        raise ValueError("paper.year must be a four-digit integer or null")
    return {
        "title": title,
        "authors": authors,
        "year": year,
        "venue": clean_optional_text(value.get("venue"), "paper.venue"),
        "doi": clean_optional_text(value.get("doi"), "paper.doi"),
    }


def validate_draft(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("facts draft must be an object")
    allowed = {
        "paper", "research_problem", "research_object", "approach", "findings",
        "contributions", "topic_terms", "limitations", "source_anchors", "confidence",
    }
    unknown = set(raw) - allowed
    if unknown:
        raise ValueError(f"facts draft has unknown fields: {', '.join(sorted(unknown))}")
    confidence = raw.get("confidence")
    if confidence is not None:
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
            raise ValueError("confidence must be a number between 0 and 1")
        confidence = float(confidence)
    return {
        "paper": validate_paper(raw.get("paper")),
        "research_problem": clean_required_text(raw.get("research_problem"), "research_problem"),
        "research_object": clean_required_text(raw.get("research_object"), "research_object"),
        "approach": clean_required_text(raw.get("approach"), "approach"),
        "findings": clean_text_list(raw.get("findings"), "findings"),
        "contributions": clean_text_list(raw.get("contributions"), "contributions"),
        "topic_terms": clean_text_list(raw.get("topic_terms"), "topic_terms", maximum=MAX_TOPIC_TERMS),
        "limitations": clean_text_list(raw.get("limitations"), "limitations"),
        "source_anchors": clean_anchors(raw.get("source_anchors")),
        "confidence": confidence,
    }


def validated_future_work_ids(
    path: Path,
    *,
    analysis_name: str,
    evidence_level: str,
    input_fingerprint: str,
) -> list[str]:
    raw = read_json(path)
    if not isinstance(raw, dict) or raw.get("status") != "ok":
        raise ValueError("future-work sidecar must be an object with status: ok")
    if raw.get("analysis") != analysis_name:
        raise ValueError("future-work sidecar analysis does not match current analysis")
    if raw.get("evidence_level") != evidence_level:
        raise ValueError("future-work sidecar evidence_level does not match facts evidence_level")
    source_fingerprint = raw.get("source_pdf_fingerprint")
    if evidence_level == "fulltext":
        if source_fingerprint != input_fingerprint:
            raise ValueError("future-work sidecar source fingerprint does not match current input")
    elif source_fingerprint not in {None, input_fingerprint}:
        raise ValueError("future-work sidecar source fingerprint does not match current input")

    items = raw.get("items")
    if not isinstance(items, list):
        raise ValueError("future-work sidecar items must be a list")
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"future-work items[{index}] must be an object")
        identifier = item.get("id")
        if not isinstance(identifier, str) or not SHA256_RE.fullmatch(identifier):
            raise ValueError(f"future-work items[{index}].id must be a SHA256 hex string")
        if identifier not in seen:
            seen.add(identifier)
            result.append(identifier)
    return result


def sidecar_path(analysis: Path) -> Path:
    return Path(str(analysis) + ".facts.json")


def finalize(
    analysis: Path,
    draft_path: Path,
    future_work_path: Path,
    input_path: Path,
    evidence_level: str,
    generator_version: str = GENERATOR_VERSION,
) -> dict[str, Any]:
    if evidence_level not in {"fulltext", "abstract_only"}:
        raise ValueError("evidence_level must be fulltext or abstract_only")
    if not analysis.is_file():
        raise ValueError(f"analysis does not exist: {analysis}")
    facts = validate_draft(read_json(draft_path))
    input_fingerprint = f"sha256:{sha256_file(input_path)}"
    future_work_ids = validated_future_work_ids(
        future_work_path,
        analysis_name=analysis.name,
        evidence_level=evidence_level,
        input_fingerprint=input_fingerprint,
    )
    payload = {
        "schema": SCHEMA,
        "kind": KIND,
        "generator_version": generator_version,
        "analysis": analysis.name,
        "input_fingerprint": input_fingerprint,
        "evidence_level": evidence_level,
        "status": "ok",
        **facts,
        "future_work_ids": future_work_ids,
    }
    output = sidecar_path(analysis)
    atomic_json(output, payload)
    return {
        "ok": True,
        "sidecar": str(output),
        "schema": SCHEMA,
        "input_fingerprint": payload["input_fingerprint"],
        "future_work_ids": future_work_ids,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    validate_parser = subcommands.add_parser("validate")
    validate_parser.add_argument("--draft", required=True, type=Path)
    finalize_parser = subcommands.add_parser("finalize")
    finalize_parser.add_argument("--analysis", required=True, type=Path)
    finalize_parser.add_argument("--draft", required=True, type=Path)
    finalize_parser.add_argument("--future-work", required=True, type=Path)
    finalize_parser.add_argument("--input", required=True, type=Path)
    finalize_parser.add_argument("--evidence-level", default="fulltext", choices=("fulltext", "abstract_only"))
    finalize_parser.add_argument("--generator-version", default=GENERATOR_VERSION)
    args = parser.parse_args()
    try:
        if args.command == "validate":
            output = {"ok": True, "facts": validate_draft(read_json(args.draft))}
        else:
            output = finalize(
                args.analysis,
                args.draft,
                args.future_work,
                args.input,
                args.evidence_level,
                args.generator_version,
            )
        print(json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, separators=(",", ":")), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
