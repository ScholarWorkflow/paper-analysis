import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[4]
FUTURE_WORK_SCRIPT = ROOT / ".apm/skills/paper-analysis/scripts/future_work.py"
PDF_RUNTIME_SCRIPT = ROOT / ".apm/skills/paper-analysis/scripts/pdf_runtime.py"


def clean_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.pop("UV_PROJECT_ENVIRONMENT", None)
    return env


def test_direct_uv_sync_from_clean_copy(tmp_path: Path) -> None:
    clone = tmp_path / "paper-analysis"
    shutil.copytree(ROOT, clone, ignore=shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache"))
    result = subprocess.run(
        ["uv", "sync", "--locked"],
        cwd=clone,
        env=clean_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_standalone_uv_run_future_work_from_clean_directory(tmp_path: Path) -> None:
    workdir = tmp_path / "standalone-future-work"
    workdir.mkdir()
    result = subprocess.run(
        ["uv", "run", str(FUTURE_WORK_SCRIPT), "--help"],
        cwd=workdir,
        env=clean_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "prepare" in result.stdout
    assert "finalize" in result.stdout
    assert not (workdir / "pyproject.toml").exists()
    assert not (workdir / ".venv").exists()


def test_standalone_uv_run_pdf_runtime_from_clean_directory(tmp_path: Path) -> None:
    workdir = tmp_path / "standalone-pdf-runtime"
    workdir.mkdir()
    result = subprocess.run(
        ["uv", "run", str(PDF_RUNTIME_SCRIPT), "--help"],
        cwd=workdir,
        env=clean_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "extract" in result.stdout
    assert "render" in result.stdout
    assert not (workdir / "pyproject.toml").exists()
    assert not (workdir / ".venv").exists()


def test_pep723_helpers_declare_release_package_metadata(tmp_path: Path) -> None:
    """The standalone dependency must come from the released distribution.

    Run each helper with ``uv run --no-project`` from a clean directory: uv
    resolves the PEP 723 metadata against the package index, not the source
    checkout, so a moving Git ref or a floating version would fail here.
    """
    for script in (FUTURE_WORK_SCRIPT, PDF_RUNTIME_SCRIPT):
        workdir = tmp_path / f"no-project-{script.stem}"
        workdir.mkdir()
        result = subprocess.run(
            ["uv", "run", "--no-project", str(script), "--help"],
            cwd=workdir,
            env=clean_env(),
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert not (workdir / "pyproject.toml").exists()
        assert not (workdir / ".venv").exists()
