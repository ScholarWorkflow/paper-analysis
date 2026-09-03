import json
import shutil
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).parents[1]
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
