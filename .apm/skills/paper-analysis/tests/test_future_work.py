import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pymupdf


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/future_work.py"
SPEC = importlib.util.spec_from_file_location("future_work", SCRIPT)
future_work = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(future_work)


class FutureWorkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)
        self.pdf = self.dir / "paper.pdf"
        doc = pymupdf.open()
        for text in ("Introduction", "Method", "Conclusion\n\nFuture work will evaluate the method on longer documents. We will share the code."):
            page = doc.new_page()
            page.insert_text((72, 72), text)
        doc.set_toc([[1, "Conclusion", 3]])
        doc.save(self.pdf)
        doc.close()
        self.prepared = future_work.prepare(self.pdf, 1)
        self.candidates = self.dir / "candidates.json"
        self.candidates.write_text(json.dumps({"candidates": self.prepared["candidates"]}), encoding="utf-8")
        self.quote = next(item["quote"] for item in self.prepared["candidates"] if "Future work" in item["quote"])
        self.item = {"quote": self.quote, "translation_zh": "未来将评估更长文档。", "source": "Conclusion", "page": 3}

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *arguments):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, arguments)], text=True, capture_output=True, check=False)

    def test_01_prepare_sha256(self):
        self.assertEqual(self.prepared["pdf_sha256"], hashlib.sha256(self.pdf.read_bytes()).hexdigest())

    def test_02_prepare_toc(self):
        self.assertEqual(self.prepared["toc"], [{"level": 1, "title": "Conclusion", "page": 3}])
        self.assertEqual(self.prepared["selection"]["toc_pages"], [3])

    def test_03_prepare_keyword_candidate(self):
        self.assertTrue(any(item["page"] == 3 and "Future work" in item["quote"] for item in self.prepared["candidates"]))

    def test_04_prepare_debug_artifacts(self):
        debug = self.dir / "debug"
        result = self.run_cli("prepare", self.pdf, "--debug-dir", debug)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((debug / "prepare.json").is_file())
        self.assertTrue((debug / "candidates.json").is_file())
        self.assertIn("<!-- PDF_PAGE: 3 -->", (debug / "candidates.md").read_text(encoding="utf-8"))

    def test_04b_prepare_cli_returns_short_summary(self):
        result = self.run_cli("prepare", self.pdf)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertNotIn("candidates", payload)
        self.assertEqual(payload["candidate_pages"], [1, 2, 3])

    def test_05_prepare_quality_and_ocr_list(self):
        self.assertEqual(len(self.prepared["page_quality"]), 3)
        self.assertEqual(self.prepared["ocr_required_pages"], [])

    def test_06_validate_generates_id(self):
        validated = future_work.validate_items([self.item], self.prepared["candidates"])
        self.assertEqual(validated[0]["id"], future_work.quote_id(self.quote))

    def test_07_validate_rejects_non_candidate(self):
        bad = dict(self.item, quote="Invented future work.")
        with self.assertRaisesRegex(ValueError, "prepared candidate"):
            future_work.validate_items([bad], self.prepared["candidates"])

    def test_08_validate_rejects_wrong_id(self):
        bad = dict(self.item, id="0" * 64)
        with self.assertRaisesRegex(ValueError, "does not match"):
            future_work.validate_items([bad], self.prepared["candidates"])

    def test_08b_validate_rejects_wrong_page(self):
        bad = dict(self.item, page=1)
        with self.assertRaisesRegex(ValueError, "quote and page"):
            future_work.validate_items([bad], self.prepared["candidates"])

    def test_09_finalize_writes_sidecar(self):
        items = self.dir / "items.json"
        items.write_text(json.dumps([self.item]), encoding="utf-8")
        analysis = self.dir / "analysis.md"
        future_work.finalize(analysis, items, self.candidates, False)
        self.assertEqual(read_json(Path(str(analysis) + ".future_work.json"))["items"][0]["quote"], self.quote)
        self.assertEqual(read_json(Path(str(analysis) + ".future_work.json"))["status"], "ok")

    def test_10_patch_replaces_only_future_section(self):
        analysis = self.dir / "analysis.md"
        analysis.write_text("# A\n\n## 局限性与批判性评价\ntext\n\n## 作者明说的未来工作（Future Work）\nold\n\n## 对自身研究的帮助评估\nhelp\n", encoding="utf-8")
        future_work.patch_analysis(analysis, future_work.validate_items([self.item], self.prepared["candidates"]))
        text = analysis.read_text(encoding="utf-8")
        self.assertIn("text", text)
        self.assertIn(self.quote, text)
        self.assertNotIn("old", text)
        self.assertIn("help", text)

    def test_11_patch_requires_exact_anchors(self):
        analysis = self.dir / "analysis.md"
        analysis.write_text("## 局限性\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "exact ordered template anchors"):
            future_work.patch_analysis(analysis, [])

    def test_12c_upgrade_full_sidecar_has_page_and_fingerprint(self):
        analysis = self.dir / "analysis.md"
        analysis.write_text(
            "## 局限性与批判性评价\ntext\n\n## 作者明说的未来工作（Future Work)\n"
            "\n## 对自身研究的帮助评估\nhelp\n".replace("（Future Work)", "（Future Work）")
            .replace("\n\n## 对自身", "\n- 原文：" + self.quote + "\n  译：未来将评估更长文档。\n  出处：Conclusion\n\n## 对自身"),
            encoding="utf-8",
        )
        prepared = self.dir / "prepared.json"
        prepared.write_text(json.dumps(self.prepared), encoding="utf-8")
        candidates = self.dir / "candidates.json"
        candidates.write_text(json.dumps({"candidates": self.prepared["candidates"]}), encoding="utf-8")
        future_work.upgrade_full_sidecar(analysis, prepared)
        payload = read_json(Path(str(analysis) + ".future_work.json"))
        self.assertEqual(payload["extractor_version"], "future-work-v1")
        self.assertEqual(payload["source_pdf_fingerprint"], "sha256:" + self.prepared["pdf_sha256"])
        self.assertEqual(payload["items"][0]["page"], 3)

    def test_12d_upgrade_full_sidecar_normalizes_source_page(self):
        analysis = self.dir / "analysis.md"
        analysis.write_text(
            "## 局限性与批判性评价\ntext\n\n## 作者明说的未来工作（Future Work）\n"
            "- 原文：" + self.quote + "\n  译：未来将评估更长文档。\n"
            "  出处：Conclusion（p.3）\n\n## 对自身研究的帮助评估\nhelp\n",
            encoding="utf-8",
        )
        prepared = self.dir / "prepared.json"
        prepared.write_text(json.dumps(self.prepared), encoding="utf-8")
        future_work.upgrade_full_sidecar(analysis, prepared)
        payload = read_json(Path(str(analysis) + ".future_work.json"))
        self.assertEqual(payload["items"][0]["source"], "Conclusion")

    def test_13_merge_ocr_replaces_only_required_page(self):
        prepared = dict(self.prepared)
        prepared["ocr_required_pages"] = [3]
        prepared_path = self.dir / "prepared.json"
        prepared_path.write_text(json.dumps(prepared), encoding="utf-8")
        ocr_path = self.dir / "ocr.json"
        ocr_path.write_text(json.dumps({"pages": {"3": "Conclusion\n\nWe will test OCR text."}}), encoding="utf-8")
        merged = future_work.merge_ocr(prepared_path, ocr_path, None)
        self.assertEqual(merged["ocr_required_pages"], [])
        self.assertTrue(any("OCR text" in item["quote"] for item in merged["candidates"]))

    def test_14_prepare_allows_exact_sentence_quote(self):
        candidates = future_work.page_candidates(
            "Future work will evaluate the method on longer documents. We will share the code.", 3
        )
        sentence = next(item["quote"] for item in candidates if item["quote"] == "Future work will evaluate the method on longer documents.")
        item = {"quote": sentence, "translation_zh": "未来将评估更长文档。", "source": "Conclusion", "page": 3}
        self.assertEqual(future_work.validate_items([item], candidates)[0]["quote"], sentence)

    def test_15_validate_rejects_oversized_quote(self):
        huge = "x" * (future_work.MAX_QUOTE_CHARS + 1)
        item = {"quote": huge, "translation_zh": "译文", "source": "Conclusion", "page": 3}
        with self.assertRaisesRegex(ValueError, "exceeds"):
            future_work.validate_items([item], [{"quote": huge, "page": 3}])


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
