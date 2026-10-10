import json
import unittest

from radar.site import build, publications, public_url
from radar.validation import read_jsonl
from tests.helpers import ROOT, sandbox, write_rows
from web.check_site import check_site


class PublicSiteTests(unittest.TestCase):
    def setUp(self):
        self.root = sandbox(self)
        self.out = self.root.parent / "site"

    def test_build_contains_only_explicit_public_projection(self):
        (self.root / "data/internal-canary.json").write_text('"PRIVATE_CANARY_417"', encoding="utf-8")
        count, files = build(self.root, self.out)
        self.assertEqual(count, 6)
        self.assertEqual(check_site(self.out), files)
        text = "".join(p.read_text(encoding="utf-8") for p in self.out.rglob("*") if p.is_file())
        for forbidden in ("PRIVATE_CANARY_417", "reportPath", "seen-items.jsonl", "dedupeReview", "tool-observations"):
            self.assertNotIn(forbidden, text)
        self.assertEqual(len(json.loads((self.out / "feed.json").read_text(encoding="utf-8"))["items"]), 6)

    def test_deterministic_build(self):
        build(self.root, self.out)
        second = self.root.parent / "second"
        build(self.root, second)
        self.assertEqual((self.out / "manifest.json").read_bytes(), (second / "manifest.json").read_bytes())

    def test_html_is_escaped(self):
        rows = read_jsonl(self.root / "data/publications.jsonl")
        rows[0]["title"] = '<script>alert("x")</script>'
        write_rows(self.root, "data/publications.jsonl", rows)
        build(self.root, self.out)
        page = (self.out / "index.html").read_text(encoding="utf-8")
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn('<script>alert("x")', page)
        check_site(self.out)

    def test_publication_requires_history_and_primary_reference(self):
        rows = read_jsonl(self.root / "data/publications.jsonl")
        rows[0]["references"][0]["url"] = "https://example.com/unrelated"
        write_rows(self.root, "data/publications.jsonl", rows)
        with self.assertRaisesRegex(ValueError, "retain the recorded"):
            publications(self.root)

    def test_extra_fields_and_private_visibility_rejected(self):
        for changes in ({"internalNotes": "not public"}, {"visibility": "private"}):
            with self.subTest(changes=changes):
                rows = read_jsonl(ROOT / "data/publications.jsonl")
                rows[0].update(changes)
                write_rows(self.root, "data/publications.jsonl", rows)
                with self.assertRaises(ValueError):
                    publications(self.root)

    def test_duplicate_unknown_and_premature_reviews_rejected(self):
        for changes in ({"id": "not-recorded"}, {"reviewedAt": "2026-10-05"}):
            with self.subTest(changes=changes):
                rows = read_jsonl(ROOT / "data/publications.jsonl")
                rows[0].update(changes)
                write_rows(self.root, "data/publications.jsonl", rows)
                with self.assertRaises(ValueError):
                    publications(self.root)
        rows = read_jsonl(ROOT / "data/publications.jsonl")
        write_rows(self.root, "data/publications.jsonl", rows + [rows[0]])
        with self.assertRaises(ValueError):
            publications(self.root)

    def test_public_urls_exclude_signed_or_credential_links(self):
        for url in ("http://example.com/", "https://user:pass@example.com/", "https://example.com/?sig=private", "https://example.com:99/", "javascript:alert(1)", "https://example.com/a\x00", "https://example.com/a\x7f"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                public_url(url)

    def test_build_refuses_repository_root_or_stale_output(self):
        with self.assertRaises(ValueError):
            build(self.root, self.root)
        self.out.mkdir()
        (self.out / "leftover").write_text("private", encoding="utf-8")
        with self.assertRaises(ValueError):
            build(self.root, self.out)

    def test_manifest_rejects_extra_and_tampered_files(self):
        build(self.root, self.out)
        (self.out / "unexpected.txt").write_text("extra", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "exactly manifest"):
            check_site(self.out)
        (self.out / "unexpected.txt").unlink()
        (self.out / "assets/app.js").write_text("tampered", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "checksum"):
            check_site(self.out)

    def test_custom_base_path_and_empty_publication(self):
        write_rows(self.root, "data/publications.jsonl", [])
        count, _ = build(self.root, self.out, "https://example.com/nested/radar/")
        self.assertEqual(count, 0)
        self.assertIn("https://example.com/nested/radar/", (self.out / "sitemap.xml").read_text())
        check_site(self.out)


if __name__ == "__main__":
    unittest.main()
