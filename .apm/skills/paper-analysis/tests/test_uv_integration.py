import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[4]
FUTURE_WORK_SCRIPT = ROOT / ".apm/skills/paper-analysis/scripts/future_work.py"
PDF_RUNTIME_SCRIPT = ROOT / ".apm/skills/paper-analysis/scripts/pdf_runtime.py"
PAPER_INPUT_SCRIPT = ROOT / ".apm/skills/paper-analysis/scripts/paper_input.py"
RUN_UV_INTEGRATION = os.environ.get("PAPER_ANALYSIS_RUN_UV_INTEGRATION") == "1"


@unittest.skipUnless(RUN_UV_INTEGRATION, "set PAPER_ANALYSIS_RUN_UV_INTEGRATION=1 with GitHub access")
class UvIntegrationTests(unittest.TestCase):
    def test_direct_uv_sync_from_clone(self):
        with tempfile.TemporaryDirectory() as temporary:
            clone = Path(temporary) / "paper-analysis"
            shutil.copytree(ROOT, clone, ignore=shutil.ignore_patterns(".venv", "__pycache__"))
            result = subprocess.run(
                ["uv", "sync", "--locked"],
                cwd=clone,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_standalone_uv_run_future_work(self):
        result = subprocess.run(
            ["uv", "run", str(FUTURE_WORK_SCRIPT), "--help"],
            cwd=Path(tempfile.gettempdir()),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("prepare", result.stdout)
        self.assertIn("finalize", result.stdout)

    def test_standalone_uv_run_pdf_runtime(self):
        result = subprocess.run(
            ["uv", "run", str(PDF_RUNTIME_SCRIPT), "--help"],
            cwd=Path(tempfile.gettempdir()),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("extract", result.stdout)
        self.assertIn("render", result.stdout)

    def test_standalone_uv_run_paper_input(self):
        result = subprocess.run(
            ["uv", "run", str(PAPER_INPUT_SCRIPT), "--help"],
            cwd=Path(tempfile.gettempdir()),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
