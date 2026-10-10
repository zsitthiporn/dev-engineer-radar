import json
import contextlib
import io
import socket
import unittest
from unittest.mock import patch
from http.client import InvalidURL
from urllib.error import HTTPError, URLError

from radar.notifications import NoRedirect, digest, main, send, teams_payload, validate_destination
from tests.helpers import ROOT


def addresses(ip):
    return lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))]


class NotificationTests(unittest.TestCase):
    def test_deterministic_public_digest(self):
        row = digest(ROOT, "2026-10-10")
        self.assertEqual(row, digest(ROOT, "2026-10-10"))
        self.assertEqual(len(row["items"]), 6)
        self.assertNotIn("reportPath", json.dumps(row))

    def test_no_articles_for_other_date(self):
        self.assertEqual(digest(ROOT, "2026-10-09")["items"], [])

    def test_teams_contract_and_bounded_card(self):
        row = digest(ROOT, "2026-10-10")
        payload = teams_payload(row)
        card = payload["attachments"][0]
        self.assertEqual(payload["type"], "message")
        self.assertEqual(card["contentType"], "application/vnd.microsoft.card.adaptive")
        self.assertEqual(card["content"]["type"], "AdaptiveCard")
        self.assertEqual(card["content"]["version"], "1.2")
        self.assertLess(len(json.dumps(payload, ensure_ascii=False).encode()), 24_000)
        self.assertIn(row["deliveryId"], json.dumps(payload))

    def test_every_article_has_a_named_link_and_compact_summary(self):
        row = digest(ROOT, "2026-10-10")
        before = json.dumps(row, ensure_ascii=False, sort_keys=True)
        card = teams_payload(row)["attachments"][0]["content"]
        stories = card["body"][1:-1]
        self.assertEqual(len(stories), len(row["items"]))
        for story, item in zip(stories, row["items"]):
            self.assertTrue(story["separator"])
            title = story["items"][0]["columns"][0]["items"][0]
            self.assertIn(item["url"], title["text"])
            self.assertNotEqual(title["text"], item["url"])
            summary = story["items"][1]
            self.assertTrue(summary["wrap"])
            self.assertEqual(summary["maxLines"], 2)
            self.assertLessEqual(len(summary["text"]), 180)
            verdict = story["items"][0]["columns"][1]["items"][0]
            self.assertEqual(verdict["text"], item["recommendation"])
        # Implementation changes must not alter the generic digest identity.
        self.assertEqual(json.dumps(row, ensure_ascii=False, sort_keys=True), before)

    def test_article_text_cannot_inject_markdown_links(self):
        row = digest(ROOT, "2026-10-10")
        row["items"][0]["title"] = "C# [tool](https://untrusted.example/)"
        row["items"][0]["summary"] = "![image](https://untrusted.example/)\n" + "ไทย " * 100
        card = teams_payload(row)["attachments"][0]["content"]
        story = card["body"][1]
        title = story["items"][0]["columns"][0]["items"][0]["text"]
        self.assertIn(r"\[tool\]\(https://untrusted.example/\)", title)
        summary = story["items"][1]["text"]
        self.assertIn(r"\!\[image\]", summary)
        self.assertNotIn("\n", summary)
        self.assertTrue(summary.endswith("…"))

    def test_markdown_url_delimiters_are_encoded_without_mutating_digest(self):
        row = digest(ROOT, "2026-10-10", "https://example.com/radar)v2/")
        original = row["items"][0]["url"]
        card = teams_payload(row)["attachments"][0]["content"]
        title = card["body"][1]["items"][0]["columns"][0]["items"][0]["text"]
        self.assertIn("https://example.com/radar%29v2/articles/", title)
        self.assertEqual(row["items"][0]["url"], original)

    def test_oversized_edition_fails_without_posting_or_dropping_articles(self):
        from unittest.mock import Mock
        row = digest(ROOT, "2026-10-10")
        row["items"] *= 30
        payload = teams_payload(row)
        self.assertEqual(len(payload["attachments"][0]["content"]["body"][1:-1]), 180)
        opener = Mock()
        with patch("radar.notifications.validate_destination"), self.assertRaisesRegex(ValueError, "24 KB"):
            send("https://example.com/", payload, opener)
        opener.open.assert_not_called()

    def test_dry_run_does_not_read_secrets_or_network(self):
        # Replace this module's OS handle; argparse may legitimately read LANGUAGE.
        with patch("radar.notifications.send") as network, patch("radar.notifications.os") as runtime:
            self.assertEqual(main(["--date", "2026-10-10"]), 0)
            network.assert_not_called()
            runtime.environ.get.assert_not_called()

    def test_send_requires_explicit_destinations(self):
        with patch("radar.notifications.send") as network:
            self.assertEqual(main(["--date", "2026-10-10", "--send"]), 1)
            network.assert_not_called()

    def test_destination_filters_private_and_malformed_addresses(self):
        for ip in ("127.0.0.1", "10.1.2.3", "169.254.169.254", "::1"):
            with self.subTest(ip=ip), self.assertRaises(ValueError):
                validate_destination("https://destination.example/?sig=secret", addresses(ip))
        for url in ("http://example.com/", "https://user:pass@example.com/", "https://example.com:88/", "https://example.com/x\x00?sig=SECRET", "https://example.com/x\x7f?sig=SECRET", "https://example.com/ไทย?sig=SECRET"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_destination(url, addresses("8.8.8.8"))
        self.assertEqual(validate_destination("https://example.com/?sig=x", addresses("8.8.8.8")), "https://example.com/?sig=x")

    def test_preflight_all_destinations_before_fanout(self):
        with patch.dict("os.environ", {"RADAR_ONE_WEBHOOK": "https://example.com/x"}, clear=True), patch("radar.notifications.validate_destination"), patch("radar.notifications.send") as network:
            self.assertEqual(main(["--date", "2026-10-10", "--send", "--destination-env", "RADAR_ONE_WEBHOOK", "--destination-env", "RADAR_TWO_WEBHOOK"]), 1)
            network.assert_not_called()

    def test_secret_url_not_exposed_on_http_or_timeout_errors(self):
        from unittest.mock import Mock
        for error in (HTTPError("https://x/?sig=SECRET", 403, "SECRET", {}, None), URLError("SECRET"), InvalidURL("SECRET"), ValueError("SECRET"), UnicodeError("SECRET")):
            opener = Mock()
            opener.open.side_effect = error
            with patch("radar.notifications.validate_destination"), self.assertRaises(ValueError) as caught:
                send("https://x/?sig=SECRET", {}, opener)
            self.assertNotIn("SECRET", str(caught.exception))
            self.assertEqual(opener.open.call_count, 1)

    def test_redirects_are_not_followed(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.example"))

    def test_cli_never_prints_control_character_webhook_secret(self):
        output = io.StringIO()
        # Real OS environments reject NUL; DEL exercises the same unsafe URL path.
        with patch.dict("os.environ", {"RADAR_TEAMS_WEBHOOK": "https://example.com/path\x7f?sig=SECRET_CANARY"}), contextlib.redirect_stderr(output), patch("radar.notifications.send") as network:
            self.assertEqual(main(["--date", "2026-10-10", "--send", "--destination-env", "RADAR_TEAMS_WEBHOOK"]), 1)
            self.assertNotIn("SECRET_CANARY", output.getvalue())
            network.assert_not_called()


if __name__ == "__main__":
    unittest.main()
