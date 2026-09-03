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
        self.assertIn("本地文本文件绝对路径（.txt/.md）", text)
        self.assertIn("TITLE: <标题>", text)
        self.assertIn("AUTHORS: <a, b>", text)
        self.assertIn("This is a deterministic text input fixture", fixture)

    def test_gap_only_fail_closed_contract_is_preserved(self):
        text = AGENT.read_text(encoding="utf-8")
        self.assertIn("失败即修正临时 JSON，绝不手工绕过", text)
        self.assertIn("任一检查失败即返回 error", text)
        self.assertIn("不得手写 Markdown", text)
        self.assertIn("不得把没有 sidecar 的状态说成完成", text)
        self.assertIn("sidecar 存在且 `status: ok`", text)

    def test_ocr_authorization_cache_and_failure_contract_is_preserved(self):
        text = AGENT.read_text(encoding="utf-8")
        self.assertIn("说明页码和逐页耗时，用户同意才 OCR", text)
        self.assertIn("先查命中缓存", text)
        self.assertIn("要我自动重识别这些页", text)
        self.assertIn("只识别坏页", text)
        self.assertIn("某页连续失败：记录失败页，不重试死磕", text)
        self.assertIn("失败页内容**不脑补**", text)

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
