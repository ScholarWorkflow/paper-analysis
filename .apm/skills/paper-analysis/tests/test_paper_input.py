import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/paper_input.py"
SPEC = importlib.util.spec_from_file_location("paper_input", SCRIPT)
paper_input = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(paper_input)


class PaperInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write_input(self, payload):
        path = (self.dir / "paper.json").resolve()
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_normalized_abstract_input(self):
        path = self.write_input({
            "schema": 1,
            "kind": "paper-analysis-input",
            "level": "abstract",
            "source": "zotero",
            "item_key": "ABC123",
            "metadata": {
                "title": "A Paper",
                "authors": ["Ada Lovelace", "Alan Turing"],
                "year": 2025,
                "venue": "TestConf",
                "doi": "10.1000/test",
            },
            "abstract": "We study a normalized input contract.",
        })
        result = paper_input.load_normalized_input(path)
        self.assertEqual(result["level"], "abstract")
        self.assertEqual(result["metadata"]["title"], "A Paper")
        self.assertEqual(result["metadata"]["authors"], ["Ada Lovelace", "Alan Turing"])
        self.assertEqual(result["abstract"], "We study a normalized input contract.")
        self.assertNotIn("source", result)
        self.assertNotIn("item_key", result)

    def test_requires_absolute_path(self):
        with self.assertRaisesRegex(ValueError, "absolute"):
            paper_input.load_normalized_input(Path("paper.json"))

    def test_rejects_wrong_kind(self):
        path = self.write_input({
            "schema": 1,
            "kind": "other",
            "level": "abstract",
            "abstract": "text",
        })
        with self.assertRaisesRegex(ValueError, "kind"):
            paper_input.load_normalized_input(path)

    def test_rejects_missing_abstract(self):
        path = self.write_input({
            "schema": 1,
            "kind": "paper-analysis-input",
            "level": "abstract",
        })
        with self.assertRaisesRegex(ValueError, "abstract"):
            paper_input.load_normalized_input(path)


if __name__ == "__main__":
    unittest.main()
