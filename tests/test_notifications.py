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
        self.assertEqual(len(card["content"]["body"]), 18)
        self.assertLess(len(json.dumps(payload, ensure_ascii=False).encode()), 24_000)
        self.assertIn(row["deliveryId"], json.dumps(payload))

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
