import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[4]
FUTURE_WORK_SCRIPT = ROOT / ".apm/skills/paper-analysis/scripts/future_work.py"


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
