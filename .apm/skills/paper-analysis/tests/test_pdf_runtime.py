import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import pymupdf


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/pdf_runtime.py"
SPEC = importlib.util.spec_from_file_location("pdf_runtime", SCRIPT)
pdf_runtime = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(pdf_runtime)


class PdfRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)
        self.pdf = (self.dir / "paper.pdf").resolve()
        document = pymupdf.open()
        page = document.new_page()
        page.insert_text((72, 72), "Paper analysis PDF runtime")
        document.save(self.pdf)
        document.close()

    def tearDown(self):
        self.temp.cleanup()

    def test_extract_writes_page_marked_text(self):
        output = (self.dir / "paper.txt").resolve()
        result = pdf_runtime.extract_pdf(self.pdf, output)
        self.assertTrue(result["ok"])
        self.assertEqual(result["pages"], 1)
        text = output.read_text(encoding="utf-8")
        self.assertIn("<!-- PDF_PAGE: 1 -->", text)
        self.assertIn("Paper analysis PDF runtime", text)

    def test_render_writes_png(self):
        output = (self.dir / "page-1.png").resolve()
        result = pdf_runtime.render_page(self.pdf, 1, output, 2.0)
        self.assertTrue(result["ok"])
        self.assertTrue(output.is_file())
        self.assertGreater(output.stat().st_size, 0)

    def test_rejects_relative_pdf_path(self):
        with self.assertRaisesRegex(ValueError, "absolute"):
            pdf_runtime.extract_pdf(Path("paper.pdf"), (self.dir / "out.txt").resolve())

    def test_update_ocr_cache_stamps_current_pdf_fingerprint(self):
        pages = (self.dir / "ocr-pages.json").resolve()
        pages.write_text(json.dumps({"pages": {"1": "exact OCR text"}}), encoding="utf-8")
        cache = (self.dir / "paper.pdf.llm_ocr.pages.json").resolve()
        result = pdf_runtime.update_ocr_cache(self.pdf, cache, pages)
        payload = json.loads(cache.read_text(encoding="utf-8"))
        expected = hashlib.sha256(self.pdf.read_bytes()).hexdigest()
        self.assertTrue(result["ok"])
        self.assertEqual(payload["schema"], 1)
        self.assertEqual(payload["pdf_sha256"], expected)
        self.assertEqual(payload["pages"], {"1": "exact OCR text"})

    def test_validate_ocr_cache_rejects_stale_pdf_fingerprint(self):
        cache = (self.dir / "paper.pdf.llm_ocr.pages.json").resolve()
        cache.write_text(
            json.dumps({"schema": 1, "pdf_sha256": "0" * 64, "pages": {"1": "stale OCR text"}}),
            encoding="utf-8",
        )
        output = (self.dir / "validated-cache.json").resolve()
        expected = hashlib.sha256(self.pdf.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, "cache fingerprint does not match"):
            pdf_runtime.validate_ocr_cache(self.pdf, cache, expected, output)
        self.assertFalse(output.exists())

    def test_update_ocr_cache_does_not_merge_stale_pages(self):
        cache = (self.dir / "paper.pdf.llm_ocr.pages.json").resolve()
        cache.write_text(
            json.dumps({"schema": 1, "pdf_sha256": "0" * 64, "pages": {"9": "stale OCR text"}}),
            encoding="utf-8",
        )
        pages = (self.dir / "ocr-pages.json").resolve()
        pages.write_text(json.dumps({"pages": {"1": "fresh OCR text"}}), encoding="utf-8")
        pdf_runtime.update_ocr_cache(self.pdf, cache, pages)
        payload = json.loads(cache.read_text(encoding="utf-8"))
        self.assertEqual(payload["pages"], {"1": "fresh OCR text"})
        self.assertNotIn("9", payload["pages"])


if __name__ == "__main__":
    unittest.main()
