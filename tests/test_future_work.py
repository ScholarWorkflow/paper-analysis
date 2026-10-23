import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import pymupdf
import pytest


ROOT = Path(__file__).resolve().parents[1] / ".apm/skills/paper-analysis"
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

    def test_13b_merged_ocr_candidate_upgrades_full_sidecar(self):
        debug = self.dir / "debug-ocr"
        debug.mkdir()
        prepared = dict(self.prepared)
        prepared["ocr_required_pages"] = [3]
        prepared_path = debug / "prepare.json"
        prepared_path.write_text(json.dumps(prepared), encoding="utf-8")
        ocr_quote = "Future work will evaluate the OCR-backed candidate."
        ocr_path = self.dir / "ocr-pages.json"
        ocr_path.write_text(json.dumps({"pages": {"3": "Conclusion\n\n" + ocr_quote}}), encoding="utf-8")
        merged = future_work.merge_ocr(prepared_path, ocr_path, debug)
        self.assertEqual(merged["ocr_required_pages"], [])
        self.assertTrue(any(item["quote"] == ocr_quote for item in merged["candidates"]))

        analysis = self.dir / "analysis-ocr.md"
        analysis.write_text(
            "## 局限性与批判性评价\ntext\n\n## 作者明说的未来工作（Future Work）\n"
            "- 原文：" + ocr_quote + "\n  译：未来将评估基于 OCR 的候选。\n"
            "  出处：Conclusion\n\n## 对自身研究的帮助评估\nhelp\n",
            encoding="utf-8",
        )
        future_work.upgrade_full_sidecar(analysis, debug / "prepare.json")
        payload = read_json(Path(str(analysis) + ".future_work.json"))
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["items"][0]["quote"], ocr_quote)
        self.assertEqual(payload["items"][0]["page"], 3)
        self.assertEqual(payload["source_pdf_fingerprint"], "sha256:" + self.prepared["pdf_sha256"])

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

    def test_16_japanese_sentences_without_spaces(self):
        for stop in ("。", "."):
            with self.subTest(stop=stop):
                sentences = [
                    f"本手法を提案した{stop}",
                    f"実験で改善を確認した{stop}",
                    f"今後は分類器を組み合わせる{stop}",
                ]
                candidates = future_work.page_candidates("".join(sentences), 4)
                self.assertEqual([item["quote"] for item in candidates], sentences)
                item = {"quote": sentences[-1], "translation_zh": "今后将组合分类器。",
                        "source": "おわりに", "page": 4}
                self.assertEqual(future_work.validate_items([item], candidates)[0]["page"], 4)
                with self.assertRaisesRegex(ValueError, "prepared candidate"):
                    future_work.validate_items([dict(item, quote=sentences[-1][:-1])], candidates)

    def test_17_ie_explanation_stays_in_exact_sentence(self):
        sentence = "In future, we will in- vestigate multiple inputs, i.e. the stock index and FAI."
        following = "We will share the results."
        candidates = future_work.page_candidates(sentence + " " + following, 4)
        self.assertEqual([item["quote"] for item in candidates], [sentence, following])
        item = {"quote": sentence, "translation_zh": "今后将研究多种输入。",
                "source": "Conclusion", "page": 4}
        self.assertEqual(future_work.validate_items([item], candidates)[0]["quote"], sentence)
        with self.assertRaisesRegex(ValueError, "prepared candidate"):
            future_work.validate_items([dict(item, quote=sentence.split(" the stock")[0])], candidates)

    def test_18_ocr_refresh_uses_same_sentence_boundaries(self):
        prepared = dict(self.prepared, ocr_required_pages=[3])
        sentences = ["手法を提案した.", "今後は分類器を組み合わせる。",
                     "We will study inputs, i.e. the index and FAI."]
        refreshed = future_work.refresh_candidates(prepared, {3: "".join(sentences)})
        self.assertEqual([item["quote"] for item in refreshed["candidates"] if item["page"] == 3], sentences)
        self.assertEqual(refreshed["ocr_required_pages"], [])


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


NON_CANDIDATE_QUOTE = (
    "In the future, we are planning to investigate adaptive search across documents."
)
SECOND_OCR_QUOTE = "In the future, we are planning to evaluate multilingual retrieval."
REPEATED_QUOTE = "We are planning to investigate adaptive retrieval."
REPEATED_CANONICAL = "We are planning to inves- tigate adaptive retrieval."
TWO_SENTENCES = "We will compare longer documents. We will publish the evaluation protocol."


def write_analysis(path, quote, source="Method"):
    path.write_text(
        "# Synthetic analysis\n\n## 局限性与批判性评价\n保留原有限制。\n\n"
        "## 作者明说的未来工作（Future Work）\n"
        f"- 原文：{quote}\n  译：计划开展后续研究。\n  出处：{source}\n\n"
        "## 对自身研究的帮助评估\n保留原有评价。\n",
        encoding="utf-8",
    )


def write_prepared(path, prepared):
    path.write_text(json.dumps(prepared, ensure_ascii=False), encoding="utf-8")


def make_non_candidate_pdf(path, blank_pages=()):
    with pymupdf.open() as document:
        for number in range(1, 23):
            page = document.new_page()
            if number in blank_pages:
                continue
            text = (
                "Method\n" + NON_CANDIDATE_QUOTE if number == 18 else
                "Method\n" + SECOND_OCR_QUOTE if number == 19 else
                "This synthetic study compares retrieval accuracy on document collections.\n"
                "The evaluation measures precision and recall under controlled conditions."
            )
            page.insert_textbox(pymupdf.Rect(72, 72, 520, 700), text, fontsize=11)
        document.save(path)


def finalize_prepared(directory, prepared, quote, page, **options):
    prepared_path = directory / "prepare.json"
    items_path = directory / "items.json"
    analysis = directory / "analysis.md"
    write_prepared(prepared_path, prepared)
    write_prepared(items_path, [{
        "quote": quote, "translation_zh": "计划开展后续研究。", "source": "Method", "page": page,
    }])
    patch = options.pop("patch", False)
    future_work.finalize(analysis, items_path, prepared_path, patch, **options)
    return read_json(future_work.sidecar_path(analysis))


@pytest.fixture
def span_material(tmp_path):
    pdf = tmp_path / "spans.pdf"
    with pymupdf.open() as document:
        for _ in range(6):
            document.new_page()
        # 新建页面后重新取得句柄，避免页面对象失效。
        first = document[0]
        first.insert_text((72, 100), "We are planning to inves-\ntigate adaptive retrieval.")
        first.insert_text((72, 220), REPEATED_QUOTE)
        first.insert_text((72, 730), "The next evaluation includes")
        for number in (2, 3):
            page = document[number - 1]
            page.insert_text((72, 26), "Synthetic study running header")
        document[1].insert_text((72, 730), "In the future, we are planning to inves-")
        document[2].insert_text((72, 72), "tigate adaptive search across documents.")
        for number in (2, 3):
            document[number - 1].insert_text((290, 820), str(number))
        document[3].insert_text((72, 72), "a separate experiment.")
        document[3].insert_text((72, 180), TWO_SENTENCES)
        document[3].insert_text((72, 300), REPEATED_QUOTE)
        for number in (5, 6):
            # 页边正文位于同一个文本块，中间句不能因位置或重复而删除。
            document[number - 1].insert_text((72, 34),
                "We are planning to compare retrieval.\n"
                "These controls remain mandatory.\n"
                "We are planning to report every result.")
        document[4].insert_text((72, 180),
            "In the future, we are planning a cost- sensitive evaluation.")
        document[4].insert_text((72, 776),
            "The next investigation compares retrieval.\nThese controls remain mandatory.")
        document[5].insert_text((72, 100),
            "The planned evaluation reports every result.")
        document.save(pdf)
    return future_work.prepare(pdf, 6)


def test_non_candidate_page_has_complete_sources_and_upgrades(tmp_path):
    pdf = tmp_path / "paper.pdf"
    make_non_candidate_pdf(pdf)
    prepared = future_work.prepare(pdf, 3)
    assert prepared["toc"] == []
    assert prepared["selection"]["last_pages"] == 3
    assert 18 not in prepared["selection"]["pages"]
    assert all(item["page"] != 18 for item in prepared["candidates"])
    assert [item["page"] for item in prepared["source_pages"]] == list(range(1, 23))
    assert NON_CANDIDATE_QUOTE in future_work.normalized_quote(prepared["source_pages"][17]["text"])
    analysis = tmp_path / "analysis.md"
    write_analysis(analysis, NON_CANDIDATE_QUOTE)
    prepared_path = tmp_path / "prepare.json"
    write_prepared(prepared_path, prepared)
    future_work.upgrade_full_sidecar(analysis, prepared_path)
    payload = read_json(future_work.sidecar_path(analysis))
    assert payload["items"][0]["quote"] == NON_CANDIDATE_QUOTE
    assert payload["items"][0]["page"] == 18
    assert payload["source_pdf_fingerprint"] == "sha256:" + hashlib.sha256(pdf.read_bytes()).hexdigest()


def test_same_page_two_sentences_remain_one_item(tmp_path, span_material):
    payload = finalize_prepared(tmp_path, span_material, TWO_SENTENCES, 4)
    assert len(payload["items"]) == 1
    assert payload["items"][0]["quote"] == TWO_SENTENCES
    assert payload["items"][0]["page"] == 4


@pytest.mark.parametrize("source,quote", [
    ("Future work will evaluate adaptive retrieval.", "Future work will evaluate adaptive retrieval."),
    ("Future work will inves-\ntigate adaptive retrieval.", "Future work will investigate adaptive retrieval."),
])
def test_source_path_preserves_existing_single_candidate_quote_and_id(tmp_path, source, quote):
    pdf = tmp_path / "single.pdf"
    with pymupdf.open() as document:
        document.new_page().insert_text((72, 72), source)
        document.save(pdf)
    prepared = future_work.prepare(pdf, 3)
    assert len(prepared["candidates"]) == 1
    candidate = prepared["candidates"][0]
    payload = finalize_prepared(tmp_path, prepared, quote, 1)
    assert payload["items"][0]["quote"] == candidate["quote"]
    assert payload["items"][0]["id"] == candidate["id"]


def test_adjacent_pages_remove_only_independent_edges_and_real_hyphen(tmp_path, span_material):
    sources = {item["page"]: item["text"] for item in span_material["source_pages"]}
    assert "In the future, we are planning to inves-" in sources[2]
    assert "tigate adaptive search across documents." in sources[3]
    assert sources[2].index("inves-") < sources[2].index("\n2\n")
    assert sources[3].index("running header") < sources[3].index("tigate adaptive")
    payload = finalize_prepared(tmp_path, span_material, NON_CANDIDATE_QUOTE, 2)
    item = payload["items"][0]
    assert item["quote"] == NON_CANDIDATE_QUOTE
    assert item["page"] == 2
    assert "2–3" in item["source"] or "2-3" in item["source"]


def test_repeated_quote_uses_first_page_and_first_offset(tmp_path, span_material):
    first_text = span_material["source_pages"][0]["text"]
    assert first_text.index("inves-\n") < first_text.index(REPEATED_QUOTE)
    analysis = tmp_path / "analysis.md"
    write_analysis(analysis, REPEATED_QUOTE)
    prepared_path = tmp_path / "prepare.json"
    write_prepared(prepared_path, span_material)
    future_work.upgrade_full_sidecar(analysis, prepared_path)
    item = read_json(future_work.sidecar_path(analysis))["items"][0]
    # 最早位置的旧候选保留断词写法，可由既有 quote/ID 核对页内位置。
    assert item["page"] == 1
    assert item["quote"] == REPEATED_CANONICAL
    assert item["id"] == hashlib.sha256(REPEATED_CANONICAL.encode()).hexdigest()


@pytest.mark.parametrize("quote,page", [
    ("An invented research plan is described here.", 4),
    ("We will study longer documents. We will publish the evaluation protocol.", 4),
    ("We are planning to compare retrieval. We are planning to report every result.", 5),
    ("The next investigation compares retrieval. The planned evaluation reports every result.", 5),
    (NON_CANDIDATE_QUOTE, 3),
    ("The next evaluation includes a separate experiment.", 1),
    ("In the future, we are planning a costsensitive evaluation.", 5),
])
def test_nonliteral_or_noncontinuous_spans_do_not_write_sidecar(tmp_path, span_material, quote, page):
    analysis = tmp_path / "analysis.md"
    write_analysis(analysis, quote)
    original = analysis.read_bytes()
    with pytest.raises(ValueError):
        finalize_prepared(tmp_path, span_material, quote, page, patch=True)
    assert analysis.read_bytes() == original
    assert not future_work.sidecar_path(analysis).exists()


def test_unmatched_upgrade_keeps_initial_analysis_without_sidecars(tmp_path, span_material):
    analysis = tmp_path / "analysis.md"
    write_analysis(analysis, "An invented research plan is described here.")
    original = analysis.read_bytes()
    prepared_path = tmp_path / "prepare.json"
    write_prepared(prepared_path, span_material)
    with pytest.raises(ValueError):
        future_work.upgrade_full_sidecar(analysis, prepared_path)
    assert analysis.read_bytes() == original
    assert not future_work.sidecar_path(analysis).exists()
    assert not Path(str(analysis) + ".facts.json").exists()


def test_finalize_rejects_foreign_digest_without_patching_analysis(tmp_path, span_material):
    analysis = tmp_path / "analysis.md"
    write_analysis(analysis, TWO_SENTENCES)
    original = analysis.read_bytes()
    with pytest.raises(ValueError):
        finalize_prepared(tmp_path, span_material, TWO_SENTENCES, 4, pdf_sha256="0" * 64, patch=True)
    assert analysis.read_bytes() == original
    assert not future_work.sidecar_path(analysis).exists()


def test_two_extra_ocr_merges_keep_first_resolution_and_good_pages(tmp_path):
    pdf = tmp_path / "paper.pdf"
    make_non_candidate_pdf(pdf, blank_pages=(19, 22))
    prepared = future_work.prepare(pdf, 3)
    # 明确模拟质量不可信；页内原话实际存在，不能只因匹配成功而保存。
    prepared = deepcopy(prepared)
    next(item for item in prepared["page_quality"] if item["page"] == 18)["tier"] = "untrusted"
    original_sources = deepcopy(prepared["source_pages"])
    assert prepared["ocr_required_pages"] == [22]
    with pytest.raises(ValueError):
        finalize_prepared(tmp_path, prepared, NON_CANDIDATE_QUOTE, 18)
    prepared_path = tmp_path / "prepare.json"
    ocr_path = tmp_path / "ocr.json"
    write_prepared(prepared_path, prepared)
    write_prepared(ocr_path, {"pages": {
        "18": NON_CANDIDATE_QUOTE,
        "22": "This synthetic study measures retrieval precision under controlled conditions.",
    }})
    first = future_work.merge_ocr(prepared_path, ocr_path, tmp_path)
    assert first["ocr_required_pages"] == []
    assert {18, 22}.issubset(first["ocr_resolved_pages"])
    assert next(item for item in first["source_pages"] if item["page"] == 18)["text"] == NON_CANDIDATE_QUOTE
    assert finalize_prepared(tmp_path, first, NON_CANDIDATE_QUOTE, 18)["items"][0]["page"] == 18
    write_prepared(prepared_path, first)
    write_prepared(ocr_path, {"pages": {"19": SECOND_OCR_QUOTE}})
    second = future_work.merge_ocr(prepared_path, ocr_path, tmp_path)
    assert {18, 19, 22}.issubset(second["ocr_resolved_pages"])
    assert second["ocr_required_pages"] == []
    sources = {item["page"]: item for item in second["source_pages"]}
    assert sources[18] == next(item for item in first["source_pages"] if item["page"] == 18)
    assert sources[19]["text"] == SECOND_OCR_QUOTE
    for item in original_sources:
        if item["page"] not in {18, 19, 22}:
            assert sources[item["page"]] == item
    assert second["selection"] == prepared["selection"]
    assert second["pdf_sha256"] == prepared["pdf_sha256"]
    assert finalize_prepared(tmp_path, second, NON_CANDIDATE_QUOTE, 18)["items"][0]["page"] == 18
    assert finalize_prepared(tmp_path, second, SECOND_OCR_QUOTE, 19)["items"][0]["page"] == 19


if __name__ == "__main__":
    unittest.main()
