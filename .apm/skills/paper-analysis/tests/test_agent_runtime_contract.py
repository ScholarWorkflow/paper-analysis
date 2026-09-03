import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).parents[1]
REPO_ROOT = Path(__file__).parents[4]
AGENT = REPO_ROOT / ".apm/agents/paper-analysis.agent.md"
PAPER_INPUT = SKILL_ROOT / "scripts/paper_input.py"
PDF_RUNTIME = SKILL_ROOT / "scripts/pdf_runtime.py"
FUTURE_WORK = SKILL_ROOT / "scripts/future_work.py"
FIXTURES = Path(__file__).parent / "fixtures"


class AgentRuntimeContractTests(unittest.TestCase):
    def test_normalized_json_uses_deterministic_helper(self):
        text = AGENT.read_text(encoding="utf-8")
        self.assertIn("PAPER_INPUT_SCRIPT", text)
        self.assertIn('uv run "$PAPER_INPUT_SCRIPT"', text)
        self.assertIn("paper_input.canonical.json", text)
        self.assertIn("只消费", text)

    def test_pdf_runtime_does_not_depend_on_host_pymupdf(self):
        text = AGENT.read_text(encoding="utf-8")
        self.assertIn("PDF_RUNTIME_SCRIPT", text)
        self.assertIn('uv run "$PDF_RUNTIME_SCRIPT" extract', text)
        self.assertIn('uv run "$PDF_RUNTIME_SCRIPT" render', text)
        self.assertNotIn("用 PyMuPDF 提取全文", text)
        self.assertNotIn("用 PyMuPDF 把", text)

    def test_text_input_contract_remains_supported(self):
        text = AGENT.read_text(encoding="utf-8")
        fixture = (FIXTURES / "paper.txt").read_text(encoding="utf-8")
        self.assertIn("绝对 `.txt`/`.md` 路径", text)
        self.assertIn("TITLE: <标题>", text)
        self.assertIn("AUTHORS: <a, b>", text)
        self.assertIn("This is a deterministic text input fixture", fixture)

    def test_all_runtime_helpers_are_script_native(self):
        for path in (PAPER_INPUT, PDF_RUNTIME, FUTURE_WORK):
            text = path.read_text(encoding="utf-8")
            self.assertIn("# /// script", text, path.name)
            self.assertIn("# requires-python", text, path.name)

    def test_pdf_helpers_bootstrap_pdf_processing_core(self):
        for path in (PDF_RUNTIME, FUTURE_WORK):
            text = path.read_text(encoding="utf-8")
            self.assertIn("pdf-processing-core @ git+https://github.com/ScholarWorkflow/pdf-processing-core.git@main", text)


if __name__ == "__main__":
    unittest.main()
