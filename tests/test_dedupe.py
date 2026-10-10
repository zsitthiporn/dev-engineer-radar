import unittest
from tests.helpers import ROOT, story
from radar.dedupe import canonical_url, decide
from radar.validation import read_yaml


class DedupeTests(unittest.TestCase):
    def setUp(self):
        self.config = read_yaml(ROOT / "config/identity.yml")
        self.old = story()

    def result(self, candidate, history=None):
        return decide(candidate, [self.old] if history is None else history, self.config)

    def test_normalizes_tracking_but_preserves_meaningful_query(self):
        self.assertEqual(canonical_url("https://GitHub.com:443/project/?utm_source=x&version=2#top"),
                         "https://github.com/project?version=2")
        self.assertNotEqual(canonical_url("https://x.com/?v=1"), canonical_url("https://x.com/?v=2"))

    def test_exact_id_and_structured_identity_are_duplicates(self):
        self.assertEqual(self.result(story())["decision"], "DUPLICATE")
        self.assertEqual(self.result(story(id="renamed-headline", event="Agent isolation ships"))["decision"], "DUPLICATE")

    def test_alias_does_not_split_story(self):
        candidate = story(id="copilot-new-headline", product="Copilot")
        candidate.pop("productKey")
        self.assertEqual(self.result(candidate)["decision"], "DUPLICATE")

    def test_same_url_different_capability_requires_review(self):
        result = self.result(story(id="copilot-models", eventKey="local-models", event="Local model routing"))
        self.assertEqual(result["decision"], "REVIEW")

    def test_unrelated_product_and_event_are_new(self):
        result = self.result(story(id="docker-build", product="Docker", productKey="docker",
                           eventKey="build-cache", event="Build cache", sourceUrl="https://docker.com/build"))
        self.assertEqual(result["decision"], "NEW")

    def test_same_url_different_product_never_auto_drops(self):
        result = self.result(story(id="docker-sandbox", product="Docker", productKey="docker"))
        self.assertEqual(result["decision"], "REVIEW")

    def test_material_milestone_with_evidence_is_update(self):
        candidate = story(id="copilot-sandbox-ga", milestone="ga", status="GA", coverage="UPDATE",
                          updateOf=self.old["id"], materialChange="milestone",
                          changeSummary="Preview becomes GA", sourceUrl="https://github.blog/changelog/ga")
        self.assertEqual(self.result(candidate)["decision"], "UPDATE")

    def test_milestone_change_without_evidence_needs_review(self):
        self.assertEqual(self.result(story(id="copilot-ga", milestone="ga"))["decision"], "REVIEW")

    def test_rewording_with_update_label_does_not_make_material_change(self):
        candidate = story(id="copilot-rewording", coverage="UPDATE", updateOf=self.old["id"],
                          changeSummary="Another announcement", materialChange="milestone")
        self.assertEqual(self.result(candidate)["decision"], "DUPLICATE")

    def test_version_change_is_not_dropped(self):
        old = story(version="1.0")
        self.assertEqual(self.result(story(id="copilot-2", version="2.0"), [old])["decision"], "REVIEW")

    def test_paraphrase_legacy_needs_review(self):
        old = {"id":"old", "product":"Copilot", "event":"Local sandbox preview",
               "status":"Preview", "sourceUrl":"https://github.blog/old"}
        candidate = story(id="new", event="Local sandbox available in preview",
                          sourceUrl="https://github.blog/new")
        self.assertEqual(self.result(candidate, [old])["decision"], "REVIEW")

    def test_cross_language_explicit_keys_are_stable(self):
        self.assertEqual(self.result(story(id="thai-story", event="เปิดตัว sandbox สำหรับ agent"))["decision"], "DUPLICATE")

    def test_id_collision_with_changed_identity_needs_review(self):
        self.assertEqual(self.result(story(milestone="ga"))["decision"], "REVIEW")

    def test_duplicate_beats_fuzzy_or_lineage_match_regardless_of_order(self):
        newer = story(id="copilot-ga", milestone="ga")
        candidate = story(id="copilot-ga-again", milestone="ga", coverage="UPDATE",
                          updateOf=self.old["id"], changeSummary="GA", materialChange="milestone")
        for rows in [[self.old, newer], [newer, self.old]]:
            self.assertEqual(self.result(candidate, rows)["decision"], "DUPLICATE")

    def test_update_parent_must_exist_and_same_product(self):
        candidate = story(id="different-ga", milestone="ga", coverage="UPDATE", updateOf="missing",
                          changeSummary="GA", materialChange="milestone")
        self.assertEqual(self.result(candidate)["decision"], "REVIEW")

    def test_repeated_new_capability_cannot_be_reported_twice(self):
        candidate = story(id="mounts", eventKey="volume-mounts", event="Volume mounts", coverage="UPDATE",
                          updateOf=self.old["id"], changeSummary="Adds mounts", materialChange="capability",
                          sourceUrl="https://github.blog/mounts")
        self.assertEqual(self.result(candidate)["decision"], "UPDATE")
        self.assertEqual(self.result(story(**{**candidate, "id":"mounts-again"}), [self.old, candidate])["decision"], "DUPLICATE")

    def test_version_punctuation_is_not_discarded(self):
        old = story(version="1.0+build.1")
        candidate = story(id="different-build", version="1.0-build.1")
        self.assertEqual(self.result(candidate, [old])["decision"], "REVIEW")

    def test_renaming_event_key_alone_is_not_material(self):
        candidate = story(id="renamed-key", eventKey="renamed-sandboxing", coverage="UPDATE",
                          updateOf=self.old["id"], materialChange="capability",
                          changeSummary="Same exact capability", sourceUrl="https://github.blog/repost")
        self.assertEqual(self.result(candidate)["decision"], "REVIEW")
