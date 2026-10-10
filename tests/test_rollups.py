import unittest
from datetime import date
from tests.helpers import ROOT, sandbox, story, write_rows
from radar.rollups import build_rollup, rebuild, render_rollup
from radar.validation import read_yaml


class RollupTests(unittest.TestCase):
    def setUp(self):
        self.config = read_yaml(ROOT / "config/identity.yml")

    def build(self, rows, kind="weekly", period="2026-W41", as_of="2026-10-10", tools=(), observations=()):
        return build_rollup(rows, tools, observations, kind, period, date.fromisoformat(as_of), self.config)

    def test_counts_events_not_repeated_mentions(self):
        rows = [story(), story(id="ga", coverage="UPDATE", lastReported="2026-10-09")]
        result = self.build(rows)
        self.assertEqual(result["counts"], {"stories":2, "new":1, "updates":1, "daysWithStories":2})
        self.assertEqual(result["products"], [{"name":"github-copilot", "count":2, "previousCount":0, "delta":2, "growthPercent":None}])

    def test_iso_week_uses_week_year(self):
        row = story(lastReported="2025-12-29")
        result = self.build([row], period="2026-W01", as_of="2026-01-04")
        self.assertEqual((result["start"], result["end"], result["counts"]["stories"]), ("2025-12-29", "2026-01-04", 1))

    def test_calendar_month_leap_and_equal_elapsed_comparison(self):
        result = self.build([], kind="monthly", period="2024-02", as_of="2024-02-29")
        self.assertEqual(result["end"], "2024-02-29")
        self.assertEqual(result["previousEnd"], "2024-01-29")
        result = self.build([], kind="monthly", period="2026-10", as_of="2026-10-10")
        self.assertEqual(result["previousEnd"], "2026-09-10")

    def test_future_rows_are_excluded(self):
        result = self.build([story(lastReported="2026-10-11")])
        self.assertEqual(result["counts"]["stories"], 0)

    def test_empty_period_has_no_invented_growth(self):
        result = self.build([])
        self.assertEqual(result["products"], [])
        self.assertEqual(result["counts"]["stories"], 0)
        self.assertIn("ไม่มี", render_rollup(result))

    def test_previous_only_signal_is_declining(self):
        result = self.build([story(lastReported="2026-10-03")])
        self.assertEqual(result["products"][0]["growthPercent"], -100.0)

    def test_latest_tool_state_and_measured_star_delta(self):
        tool = {"id":"copilot", "name":"Copilot", "firstSeen":"2026-10-01"}
        obs = [dict(id="a", toolId="copilot", observedAt="2026-10-03", recommendation="Watch",
                    maturity="Preview", metrics={"stars":0}),
               dict(id="b", toolId="copilot", observedAt="2026-10-09", recommendation="Try",
                    maturity="Preview", metrics={"stars":10}),
               dict(id="c", toolId="copilot", observedAt="2026-10-11", recommendation="Skip", maturity="Preview")]
        result = self.build([], tools=[tool], observations=obs)
        self.assertEqual(result["tools"][0]["recommendation"], "Try")
        self.assertEqual(result["tools"][0]["starsDelta"], 10)
        self.assertIsNone(result["tools"][0]["starsGrowthPercent"])

    def test_tool_without_observation_is_unknown(self):
        result = self.build([], tools=[{"id":"tool", "name":"Tool", "firstSeen":"2026-10-01"}])
        self.assertIsNone(result["tools"][0]["recommendation"])
        self.assertIsNone(result["tools"][0]["starsDelta"])

    def test_order_does_not_change_rollup(self):
        rows = [story(), story(id="second", product="Docker", productKey="docker")]
        self.assertEqual(self.build(rows), self.build(list(reversed(rows))))

    def test_case_variants_count_one_tag_per_event(self):
        result = self.build([story(tags=["AI", "ai"])])
        self.assertEqual(result["tags"][0]["count"], 1)

    def test_observation_story_links_populate_legacy_tool_count(self):
        tool = {"id":"copilot", "name":"Copilot", "firstSeen":"2026-10-01"}
        obs = {"id":"a", "toolId":"copilot", "observedAt":"2026-10-10",
               "recommendation":"Try", "maturity":"Preview", "storyIds":["copilot-sandbox-preview"]}
        result = self.build([story()], tools=[tool], observations=[obs])
        self.assertEqual(result["tools"][0]["storyCount"], 1)

    def test_invalid_period_rejected(self):
        for kind, period in [("weekly","2026-W54"), ("monthly","2026-13"), ("weekly","../escape")]:
            with self.subTest(period=period), self.assertRaises(ValueError):
                self.build([], kind=kind, period=period)

    def test_rebuild_and_drift_check(self):
        root = sandbox(self)
        self.assertEqual(rebuild(root, date(2026,10,10)), [])
        self.assertEqual(rebuild(root, date(2026,10,10), check=True), [])
        p = root / "reports/weekly/2026/2026-W41.md"
        self.assertTrue(p.is_file())
        p.write_text("stale", encoding="utf-8")
        self.assertTrue(rebuild(root, date(2026,10,10), check=True))

    def test_rebuild_rejects_bad_data_before_any_write(self):
        root = sandbox(self)
        write_rows(root, "data/seen-items.jsonl", [story(id="bad id")])
        with self.assertRaises(ValueError):
            rebuild(root, date(2026,10,10))
