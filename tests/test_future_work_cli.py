import json
import shutil
import subprocess
import sys
import hashlib
from pathlib import Path

from test_future_work import NON_CANDIDATE_QUOTE, make_non_candidate_pdf, write_analysis

SKILL_ROOT = Path(__file__).resolve().parents[1] / ".apm/skills/paper-analysis"
SCRIPT = SKILL_ROOT / "scripts/future_work.py"
FIXTURES = Path(__file__).parent / "fixtures"


def run_cli(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        text=True,
        capture_output=True,
        check=False,
    )


def test_prepare_validate_finalize_checked_in_fixtures(tmp_path: Path) -> None:
    debug = tmp_path / "debug"
    analysis = tmp_path / "analysis.md"
    shutil.copyfile(FIXTURES / "analysis.md", analysis)

    prepared = run_cli(
        "prepare",
        FIXTURES / "future_work.pdf",
        "--debug-dir",
        debug,
    )
    assert prepared.returncode == 0, prepared.stderr
    prepare_summary = json.loads(prepared.stdout)
    assert prepare_summary["result"] == "ok"
    assert prepare_summary["candidate_count"] >= 1
    assert prepare_summary["ocr_required_pages"] == []
    assert (debug / "prepare.json").is_file()
    assert (debug / "candidates.json").is_file()

    validated = run_cli(
        "validate",
        "--items",
        FIXTURES / "future_work_items.json",
        "--candidates",
        debug / "candidates.json",
    )
    assert validated.returncode == 0, validated.stderr
    validate_payload = json.loads(validated.stdout)
    assert validate_payload["ok"] is True
    assert validate_payload["items"][0]["quote"] == (
        "Future work will evaluate the method on longer documents."
    )

    finalized = run_cli(
        "finalize",
        "--analysis",
        analysis,
        "--items",
        FIXTURES / "future_work_items.json",
        "--candidates",
        debug / "candidates.json",
        "--patch",
        "--pdf-sha256",
        prepare_summary["pdf_sha256"],
    )
    assert finalized.returncode == 0, finalized.stderr
    finalize_payload = json.loads(finalized.stdout)
    assert finalize_payload["ok"] is True
    assert finalize_payload["items"] == 1

    sidecar = Path(str(analysis) + ".future_work.json")
    sidecar_payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert sidecar_payload["status"] == "ok"
    assert sidecar_payload["source_pdf_fingerprint"] == (
        "sha256:" + prepare_summary["pdf_sha256"]
    )
    assert sidecar_payload["items"][0]["page"] == 1

    patched = analysis.read_text(encoding="utf-8")
    assert "## 作者明说的未来工作（Future Work）" in patched
    assert "Future work will evaluate the method on longer documents." in patched
    assert patched.index("## 局限性与批判性评价") < patched.index(
        "## 作者明说的未来工作（Future Work）"
    ) < patched.index("## 对自身研究的帮助评估")


def test_prepared_non_candidate_cli_entries_and_upgrade_to_facts(tmp_path: Path) -> None:
    pdf = tmp_path / "paper.pdf"
    make_non_candidate_pdf(pdf)
    debug = tmp_path / "debug"
    prepared = run_cli("prepare", pdf, "--last-pages", 3, "--debug-dir", debug)
    assert prepared.returncode == 0, prepared.stderr
    prepare_payload = json.loads((debug / "prepare.json").read_text(encoding="utf-8"))
    assert 18 not in prepare_payload["selection"]["pages"]
    assert all(item["page"] != 18 for item in prepare_payload["candidates"])
    assert len(prepare_payload["source_pages"]) == 22
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    assert prepare_payload["pdf_sha256"] == digest
    # 三个入口共用无候选兄弟文件的原文输入，不以旧候选掩盖接线问题。
    (debug / "candidates.json").unlink()
    assert not (debug / "candidates.json").exists()
    items = tmp_path / "items.json"
    items.write_text(json.dumps([{
        "quote": NON_CANDIDATE_QUOTE,
        "translation_zh": "计划研究跨文档的自适应检索。",
        "source": "Method", "page": 18,
    }]), encoding="utf-8")
    analysis = tmp_path / "finalized.md"
    write_analysis(analysis, NON_CANDIDATE_QUOTE)
    original = analysis.read_bytes()
    validated = run_cli("validate", "--items", items, "--candidates", debug / "prepare.json")
    assert validated.returncode == 0, validated.stderr
    validation = json.loads(validated.stdout)
    assert validation["ok"] is True
    assert validation["items"][0]["quote"] == NON_CANDIDATE_QUOTE
    assert validation["items"][0]["page"] == 18
    assert analysis.read_bytes() == original
    assert not Path(str(analysis) + ".future_work.json").exists()
    invalid_items = tmp_path / "invalid-items.json"
    invalid_items.write_text(json.dumps([{
        "quote": "In the future, we are planning to study adaptive search across documents.",
        "translation_zh": "计划开展后续研究。", "source": "Method", "page": 18,
    }]), encoding="utf-8")
    rejected = run_cli("validate", "--items", invalid_items,
                       "--candidates", debug / "prepare.json")
    assert rejected.returncode != 0
    assert json.loads(rejected.stderr)["ok"] is False
    assert analysis.read_bytes() == original
    assert not Path(str(analysis) + ".future_work.json").exists()
    finalized = run_cli("finalize", "--analysis", analysis, "--items", items,
                        "--candidates", debug / "prepare.json", "--patch")
    assert finalized.returncode == 0, finalized.stderr
    assert json.loads(finalized.stdout)["ok"] is True
    finalized_payload = json.loads(Path(str(analysis) + ".future_work.json").read_text(encoding="utf-8"))
    assert finalized_payload["items"][0]["quote"] == NON_CANDIDATE_QUOTE
    assert finalized_payload["items"][0]["page"] == 18
    assert finalized_payload["source_pdf_fingerprint"] == "sha256:" + digest

    full_analysis = tmp_path / "analysis.md"
    write_analysis(full_analysis, NON_CANDIDATE_QUOTE)
    upgraded = run_cli("upgrade-full-sidecar", "--analysis", full_analysis,
                       "--prepared", debug / "prepare.json")
    assert upgraded.returncode == 0, upgraded.stderr
    assert json.loads(upgraded.stdout)["ok"] is True
    future_path = Path(str(full_analysis) + ".future_work.json")
    future = json.loads(future_path.read_text(encoding="utf-8"))
    assert future["status"] == "ok"
    assert future["schema"] == 1
    assert future["extractor_version"] == "future-work-v1"
    assert future["evidence_level"] == "fulltext"
    assert future["analysis"] == full_analysis.name
    assert future["source_pdf_fingerprint"] == "sha256:" + digest
    assert len(future["items"]) == 1
    item = future["items"][0]
    assert set(item) == {"id", "quote", "translation_zh", "source", "page"}
    assert item["quote"] == NON_CANDIDATE_QUOTE
    assert item["page"] == 18
    assert item["id"] == hashlib.sha256(NON_CANDIDATE_QUOTE.encode()).hexdigest()
    draft = tmp_path / "facts-draft.json"
    draft.write_text(json.dumps({
        "paper": {"title": "Synthetic retrieval study", "authors": ["A. Example"],
                  "year": 2026, "venue": "Synthetic venue", "doi": "10.0000/example"},
        "research_problem": "Measure retrieval accuracy.",
        "research_object": "Synthetic document collections.",
        "approach": "Adaptive retrieval.",
        "findings": ["The controlled evaluation measures precision."],
        "contributions": ["Describes the evaluation protocol."],
        "topic_terms": ["retrieval"], "limitations": ["Synthetic inputs only."],
        "source_anchors": {"approach": ["Method"]}, "confidence": 0.9,
    }), encoding="utf-8")
    facts = subprocess.run([
        sys.executable, str(SKILL_ROOT / "scripts/facts.py"), "finalize",
        "--analysis", str(full_analysis), "--draft", str(draft),
        "--future-work", str(future_path), "--input", str(pdf),
        "--evidence-level", "fulltext",
    ], text=True, capture_output=True, check=False)
    assert facts.returncode == 0, facts.stderr
    assert json.loads(facts.stdout)["ok"] is True
    payload = json.loads(Path(str(full_analysis) + ".facts.json").read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert payload["input_fingerprint"] == "sha256:" + digest
    assert payload["future_work_ids"] == [item["id"]]
