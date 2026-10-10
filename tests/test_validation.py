import unittest
from tests.helpers import ROOT, sandbox, story, write_rows
from radar.validation import read_jsonl, read_yaml, validate_record, validate_repository


class ValidationTests(unittest.TestCase):
    def test_existing_repository_remains_valid(self):
        self.assertEqual(validate_repository(ROOT), [])

    def test_new_record_and_legacy_are_valid(self):
        self.assertEqual(validate_record(story(), "story", ROOT), [])
        legacy = read_jsonl(ROOT / "data/seen-items.jsonl")[0]
        self.assertEqual(validate_record(legacy, "story", ROOT), [])

    def test_schema_rejects_invalid_values(self):
        for changes in [dict(firstSeen="2026-02-30"), dict(id="../escape"),
                        dict(sourceUrl="file:///secret"), dict(sourceUrl="https://user:pass@example.com"),
                        dict(tags=["AI", "AI"]), dict(coverage="maybe"), dict(extra=True),
                        dict(schemaVersion=3), dict(score=float("nan"))]:
            with self.subTest(changes=changes):
                self.assertTrue(validate_record(story(**changes), "story", ROOT))

    def test_update_requires_evidence_and_parent(self):
        self.assertTrue(validate_record(story(coverage="UPDATE"), "story", ROOT))

    def test_rejects_duplicate_yaml_keys(self):
        root = sandbox(self)
        p = root / "config/topics.yml"
        p.write_text("version: 1\nversion: 2\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            read_yaml(p)

    def test_rejects_duplicate_json_keys_and_nonfinite_numbers(self):
        root = sandbox(self)
        p = root / "data/seen-items.jsonl"
        for data in ['{"id":"a","id":"b"}\n', '{"score":NaN}\n', '\n', '[]\n']:
            p.write_text(data, encoding="utf-8")
            with self.subTest(data=data), self.assertRaises(ValueError):
                read_jsonl(p)

    def test_repository_rejects_duplicate_id_bad_dates_and_report(self):
        for change in [dict(lastReported="2026-10-01"), dict(reportPath="../README.md"),
                       dict(reportPath="reports/2026/2026-10-11.md")]:
            root = sandbox(self)
            write_rows(root, "data/seen-items.jsonl", [story(**change)])
            self.assertTrue(validate_repository(root))
        root = sandbox(self)
        rows = read_jsonl(root / "data/seen-items.jsonl")
        write_rows(root, "data/seen-items.jsonl", rows + [rows[0]])
        self.assertTrue(validate_repository(root))

    def test_repository_requires_valid_update_lineage(self):
        root = sandbox(self)
        write_rows(root, "data/seen-items.jsonl", [story(coverage="UPDATE", updateOf="missing",
                   materialChange="capability", changeSummary="Adds mounts")])
        self.assertTrue(validate_repository(root))

    def test_repository_rejects_unknown_tools_and_invalid_weights(self):
        root = sandbox(self)
        write_rows(root, "data/seen-items.jsonl", [story(toolIds=["missing"])])
        self.assertTrue(validate_repository(root))
        root = sandbox(self)
        p = root / "config/topics.yml"
        p.write_text(p.read_text(encoding="utf-8").replace("ai_developer_tools: 30", "ai_developer_tools: 31"), encoding="utf-8")
        self.assertTrue(validate_repository(root))

    def test_report_requires_explicit_item_marker(self):
        root = sandbox(self)
        write_rows(root, "data/tool-observations.jsonl", [])
        write_rows(root, "data/seen-items.jsonl", [story()])
        self.assertTrue(validate_repository(root))
        p = root / "reports/2026/2026-10-10.md"
        p.write_text(p.read_text(encoding="utf-8") + "\n<!-- radar:item copilot-sandbox-preview -->\n", encoding="utf-8")
        self.assertEqual(validate_repository(root), [])

    def test_observation_foreign_keys_and_measurements(self):
        root = sandbox(self)
        write_rows(root, "data/tool-observations.jsonl", [dict(schemaVersion=1,
                   id="missing-2026-10-10", toolId="missing", observedAt="2026-10-10",
                   recommendation="Watch", maturity="Preview", sourceUrl="https://example.com",
                   notes="Measured", metrics={"stars":-1}, storyIds=["unknown"])])
        self.assertTrue(validate_repository(root))

    def test_v2_primary_keys_must_match_curated_product_alias(self):
        root = sandbox(self)
        write_rows(root, "data/seen-items.jsonl", [story(productKey="docker")])
        self.assertTrue(any("productKey" in e for e in validate_repository(root)))

    def test_semantic_duplicate_cannot_be_appended_with_new_id(self):
        root = sandbox(self)
        first = story()
        second = story(id="new-title", event="Different headline")
        write_rows(root, "data/seen-items.jsonl", [first, second])
        p = root / "reports/2026/2026-10-10.md"
        p.write_text(p.read_text(encoding="utf-8") + "\n<!-- radar:item copilot-sandbox-preview -->\n<!-- radar:item new-title -->\n", encoding="utf-8")
        self.assertTrue(any("duplicate" in e for e in validate_repository(root)))

    def test_ambiguous_event_requires_recorded_review(self):
        root = sandbox(self)
        row = story(id="independent-capability", product="C# Dev Kit", productKey="csharp-dev-kit",
                    sourceUrl="https://devblogs.microsoft.com/dotnet/faster-lighter-csharp-dev-kit/")
        old = read_jsonl(root / "data/seen-items.jsonl")
        write_rows(root, "data/seen-items.jsonl", old + [row])
        p = root / "reports/2026/2026-10-10.md"
        p.write_text(p.read_text(encoding="utf-8") + "\n<!-- radar:item independent-capability -->\n", encoding="utf-8")
        self.assertTrue(any("dedupeReview" in e for e in validate_repository(root)))
        row["dedupeReview"] = {"matchedId":"csharp-dev-kit-11-performance-rearchitecture",
                              "reason":"Separate capability from startup rearchitecture", "reviewedAt":"2026-10-10"}
        write_rows(root, "data/seen-items.jsonl", old + [row])
        self.assertEqual(validate_repository(root), [])

    def test_alias_validation_uses_dedupe_normalization(self):
        root = sandbox(self)
        p = root / "config/identity.yml"
        p.write_text(p.read_text(encoding="utf-8") + "  another-product:\n    - GitHub   Copilot\n", encoding="utf-8")
        self.assertTrue(any("ambiguous alias" in e for e in validate_repository(root)))

    def test_valid_update_can_link_to_legacy_product(self):
        root = sandbox(self)
        row = story(id="copilot-volume-mounts-ga", event="Volume mounts", eventKey="volume-mounts",
                    milestone="ga", coverage="UPDATE", updateOf="github-copilot-local-sandbox-ga",
                    materialChange="capability", changeSummary="Adds volume mounts")
        old = read_jsonl(root / "data/seen-items.jsonl")
        write_rows(root, "data/seen-items.jsonl", old + [row])
        p = root / "reports/2026/2026-10-10.md"
        p.write_text(p.read_text(encoding="utf-8") + "\n<!-- radar:item copilot-volume-mounts-ga -->\n", encoding="utf-8")
        self.assertEqual(validate_repository(root), [])

    def test_every_supplied_review_requires_prior_reference_and_date(self):
        for review in [{"matchedId":"missing", "reason":"A review referencing an absent story", "reviewedAt":"2026-10-10"},
                       {"matchedId":"dotnet-11-rc1-go-live", "reason":"An independent tool with similar naming", "reviewedAt":"2026-10-11"}]:
            with self.subTest(review=review):
                root = sandbox(self)
                row = story(id="independent-tool", product="Independent Tool", productKey="independent-tool",
                            sourceUrl="https://independent.example/release", dedupeReview=review)
                old = read_jsonl(root / "data/seen-items.jsonl")
                write_rows(root, "data/seen-items.jsonl", old + [row])
                p = root / "reports/2026/2026-10-10.md"
                p.write_text(p.read_text(encoding="utf-8") + "\n<!-- radar:item independent-tool -->\n", encoding="utf-8")
                self.assertTrue(any("dedupeReview" in e for e in validate_repository(root)))
