import json
import subprocess
import sys
import unittest
from datetime import date
from pathlib import Path
from tests.helpers import ROOT, sandbox, story
from radar.rollups import rebuild


class CliTests(unittest.TestCase):
    def run_cli(self, root, *args):
        return subprocess.run([sys.executable, "-m", "radar", "--root", str(root), *args],
                              cwd=ROOT, capture_output=True, text=True, encoding="utf-8")

    def test_validate_reports_success_and_data_failure(self):
        root = sandbox(self)
        result = self.run_cli(root, "validate")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Validation passed", result.stdout)
        (root / "data/seen-items.jsonl").write_text("bad\n", encoding="utf-8")
        self.assertNotEqual(self.run_cli(root, "validate").returncode, 0)

    def test_dedupe_returns_machine_decision_without_mutation(self):
        root = sandbox(self)
        candidate = root / "candidate.json"
        candidate.write_text(json.dumps(story()), encoding="utf-8")
        before = (root / "data/seen-items.jsonl").read_bytes()
        result = self.run_cli(root, "dedupe", str(candidate))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(json.loads(result.stdout)["decision"], {"NEW","REVIEW"})
        self.assertEqual((root / "data/seen-items.jsonl").read_bytes(), before)

    def test_dedupe_rejects_invalid_candidate_and_corrupt_history(self):
        root = sandbox(self)
        candidate = root / "candidate.json"
        candidate.write_text('{"id":"bad"}', encoding="utf-8")
        self.assertNotEqual(self.run_cli(root, "dedupe", str(candidate)).returncode, 0)
        candidate.write_text(json.dumps(story()), encoding="utf-8")
        (root / "data/seen-items.jsonl").write_text("bad\n", encoding="utf-8")
        self.assertNotEqual(self.run_cli(root, "dedupe", str(candidate)).returncode, 0)

    def test_rollup_reads_saved_asof_and_detects_drift(self):
        root = sandbox(self)
        rebuild(root, date(2026,10,10))
        self.assertEqual(self.run_cli(root, "rollup", "--check").returncode, 0)
        (root / "reports/weekly/2026/2026-W41.md").write_text("stale", encoding="utf-8")
        self.assertNotEqual(self.run_cli(root, "rollup", "--check").returncode, 0)

    def test_rollup_requires_asof_without_manifest_and_rejects_invalid_date(self):
        root = sandbox(self)
        manifest = root / "data/rollup-state.json"
        manifest.unlink(missing_ok=True)
        self.assertNotEqual(self.run_cli(root, "rollup").returncode, 0)
        self.assertNotEqual(self.run_cli(root, "rollup", "--as-of", "2026-02-30").returncode, 0)

    def test_append_only_comparison_rejects_history_edits(self):
        root = sandbox(self)
        for args in [["init"], ["add", "data/seen-items.jsonl", "data/tool-observations.jsonl"],
                     ["-c", "user.name=Test", "-c", "user.email=test@local.invalid", "commit", "-m", "baseline"]]:
            subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
        self.assertEqual(self.run_cli(root, "validate", "--base", sha).returncode, 0)
        p = root / "data/seen-items.jsonl"
        p.write_text(p.read_text(encoding="utf-8").replace('"status":"GA"', '"status":"Changed"', 1), encoding="utf-8")
        result = self.run_cli(root, "validate", "--base", sha)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("append-only", result.stderr)
