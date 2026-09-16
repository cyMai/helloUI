import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "extract_design.py"


class ExtractDesignTests(unittest.TestCase):
    def test_extracts_candidates_without_changing_approved_design(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "DESIGN.md").write_text("# 已确认规则\n保持当前按钮语义。\n", encoding="utf-8")
            (root / "index.html").write_text(
                '<meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="style.css"><main class="card"><a class="button">查看</a></main>',
                encoding="utf-8",
            )
            (root / "detail.html").write_text(
                '<style>.button { background: #f60; }</style><main class="card"><a class="button">查看</a></main>',
                encoding="utf-8",
            )
            (root / "style.css").write_text(
                ':root { --accent: #176b50; } .button { background: var(--accent); } .card { background: var(--accent); width: 720px; } @media (max-width: 600px) { .card { width: 100%; } }',
                encoding="utf-8",
            )

            result = subprocess.run([sys.executable, str(SCRIPT), "--project-root", str(root)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            evidence = json.loads((root / ".hello-ui" / "evidence.json").read_text(encoding="utf-8"))
            proposals = (root / ".hello-ui" / "proposals.md").read_text(encoding="utf-8")

            self.assertEqual((root / "DESIGN.md").read_text(encoding="utf-8"), "# 已确认规则\n保持当前按钮语义。\n")
            self.assertIn("--accent", evidence["tokens"])
            self.assertTrue(any("@media" in q["query"] for q in evidence["queries"]))
            self.assertTrue(any(item["class"] == "button" for item in evidence["shared_classes"]))
            self.assertTrue(any(item["kind"] == "missing-viewport" for item in evidence["issues"]))
            self.assertTrue(any(item["kind"] == "fixed-width-review" for item in evidence["issues"]))
            self.assertTrue(any(item["file"] == "detail.html" for item in evidence["css_rules"]))
            self.assertIn("待审核", proposals)


if __name__ == "__main__":
    unittest.main()
