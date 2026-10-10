import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def story(**changes):
    row = dict(schemaVersion=2, id="copilot-sandbox-preview", product="GitHub Copilot",
               productKey="github-copilot", event="Local sandboxing", eventKey="local-sandboxing",
               milestone="preview", firstSeen="2026-10-10", lastReported="2026-10-10",
               publishedAt="2026-10-09", status="Preview", coverage="NEW", tags=["AI"],
               sourceType="official", sourceUrl="https://github.blog/changelog/sandbox",
               reportPath="reports/2026/2026-10-10.md", evidenceSummary="Official preview release")
    row.update(changes)
    return row


def sandbox(test):
    temp_parent = ROOT.parent / "test-temp"
    temp_parent.mkdir(exist_ok=True)
    temp = tempfile.TemporaryDirectory(dir=temp_parent)
    test.addCleanup(temp.cleanup)
    root = Path(temp.name) / "repo"
    shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    return root


def write_rows(root, path, rows):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
