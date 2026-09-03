import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/facts.py"
SPEC = importlib.util.spec_from_file_location("facts", SCRIPT)
facts = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(facts)


class FactsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)
        self.analysis = self.dir / "analysis.md"
        self.analysis.write_text("# analysis\n", encoding="utf-8")
        self.input = self.dir / "paper.txt"
        self.input.write_text("full paper input\n", encoding="utf-8")
        self.future = self.dir / "analysis.md.future_work.json"
        self.future_id = hashlib.sha256(b"future quote").hexdigest()
        self.future.write_text(
            json.dumps({"status": "ok", "items": [{"id": self.future_id}]}),
            encoding="utf-8",
        )
        self.draft = self.dir / "facts-draft.json"
        self.draft.write_text(json.dumps(self.valid_draft()), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def valid_draft(self):
        return {
            "paper": {
                "title": "Paper title",
                "authors": ["A. Author"],
                "year": 2026,
                "venue": "Venue",
                "doi": "10.0000/example",
            },
            "research_problem": "Detect a concrete failure mode.",
            "research_object": "Documents with long-range dependencies.",
            "approach": "A retrieval-augmented encoder.",
            "findings": ["Improves the primary metric by 4 points."],
            "contributions": ["Introduces the benchmark and model."],
            "topic_terms": ["retrieval", "long documents"],
            "limitations": ["Evaluation covers one language."],
            "source_anchors": {
                "approach": ["§3 Method"],
                "findings": ["§5 Results"],
            },
            "confidence": 0.9,
        }

    def test_validate_draft_is_compact_and_strict(self):
        payload = facts.validate_draft(self.valid_draft())
        self.assertEqual(payload["paper"]["title"], "Paper title")
        self.assertEqual(payload["topic_terms"], ["retrieval", "long documents"])
        bad = self.valid_draft()
        bad["invented"] = "nope"
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            facts.validate_draft(bad)

    def test_finalize_writes_versioned_fingerprinted_sidecar(self):
        result = facts.finalize(
            self.analysis,
            self.draft,
            self.future,
            self.input,
            "fulltext",
        )
        sidecar = Path(result["sidecar"])
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        expected = hashlib.sha256(self.input.read_bytes()).hexdigest()
        self.assertEqual(payload["schema"], 1)
        self.assertEqual(payload["kind"], "paper-analysis-facts")
        self.assertEqual(payload["generator_version"], "facts-v1")
        self.assertEqual(payload["input_fingerprint"], "sha256:" + expected)
        self.assertEqual(payload["evidence_level"], "fulltext")
        self.assertEqual(payload["status"], "ok")

    def test_future_work_ids_are_joined_only_from_validated_sidecar(self):
        facts.finalize(self.analysis, self.draft, self.future, self.input, "fulltext")
        payload = json.loads(Path(str(self.analysis) + ".facts.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["future_work_ids"], [self.future_id])
        raw = self.valid_draft()
        raw["future_work_ids"] = ["0" * 64]
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            facts.validate_draft(raw)

    def test_invalid_future_work_sidecar_fails_closed(self):
        self.future.write_text(json.dumps({"status": "error", "items": []}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "status: ok"):
            facts.finalize(self.analysis, self.draft, self.future, self.input, "fulltext")

    def test_input_fingerprint_changes_when_source_changes(self):
        first = facts.finalize(self.analysis, self.draft, self.future, self.input, "fulltext")
        self.input.write_text("changed full paper input\n", encoding="utf-8")
        second = facts.finalize(self.analysis, self.draft, self.future, self.input, "fulltext")
        self.assertNotEqual(first["input_fingerprint"], second["input_fingerprint"])


if __name__ == "__main__":
    unittest.main()
