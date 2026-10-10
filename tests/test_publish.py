import json
import contextlib
import io
import unittest
from unittest.mock import patch

from radar.publish import publish, main
from tests.helpers import sandbox
from radar.site import build


class Response:
    def __init__(self, value):
        self.value = value
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return json.dumps(self.value).encode()


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.root = sandbox(self)
        self.out = self.root.parent / "site"
        build(self.root, self.out)

    def test_replaces_only_site_tree_and_uses_nonforced_update(self):
        calls = []
        responses = iter([{"object": {"sha": "oldhead"}}, {"tree": {"sha": "root-tree"}},
                          {"sha": "newsite"}, {"tree": [{"path": ".github", "sha": "kept"}, {"path": "site", "sha": "oldsite"}]},
                          {"sha": "newroot"}, {"sha": "newhead"}, {"ref": "refs/heads/main"}])
        class Opener:
            def open(self, request, timeout):
                calls.append(request)
                return Response(next(responses))
        with patch("radar.publish.build_opener", return_value=Opener()):
            publish(self.out, "TEST_ONLY_TOKEN")
        root_update = json.loads(calls[4].data)
        self.assertEqual(root_update, {"base_tree": "root-tree", "tree": [{"path": "site", "mode": "040000", "type": "tree", "sha": "newsite"}]})
        self.assertEqual(json.loads(calls[5].data)["parents"], ["oldhead"])
        self.assertEqual(json.loads(calls[6].data), {"sha": "newhead", "force": False})
        self.assertTrue(all("zsitthiporn/dev-engineer-radar-web/" in r.full_url for r in calls))
        exported = json.loads(calls[2].data)["tree"]
        self.assertTrue(all(not r["path"].startswith("data/") for r in exported))

    def test_missing_token_or_invalid_export_does_not_use_network(self):
        with patch("radar.publish.build_opener") as network:
            with self.assertRaises(ValueError):
                publish(self.out, "")
            network.assert_not_called()

        (self.out / "private.txt").write_text("canary")
        with patch("radar.publish.build_opener") as network:
            with self.assertRaises(ValueError):
                publish(self.out, "TEST_ONLY_TOKEN")
            network.assert_not_called()

    def test_malformed_token_rejected_without_disclosure_or_network(self):
        for token in ("TOKEN_CANARY\ninvalid", "TOKEN_CANARY\x00", "TOKEN_CANARY\x7f", "TOKEN_CANARY\t"):
            with self.subTest(token=repr(token)), patch("radar.publish.build_opener") as network:
                with self.assertRaises(ValueError) as caught:
                    publish(self.out, token)
                self.assertNotIn("TOKEN_CANARY", str(caught.exception))
                network.assert_not_called()

    def test_transport_value_error_does_not_disclose_token(self):
        from unittest.mock import Mock
        opener = Mock()
        opener.open.side_effect = ValueError("Bearer TOKEN_CANARY")
        with patch("radar.publish.build_opener", return_value=opener), self.assertRaises(ValueError) as caught:
            publish(self.out, "TOKEN_CANARY")
        self.assertNotIn("TOKEN_CANARY", str(caught.exception))

    def test_cli_never_prints_malformed_token(self):
        output = io.StringIO()
        with patch.dict("os.environ", {"WEB_PUBLISH_TOKEN": "TOKEN_CANARY\ninvalid"}), contextlib.redirect_stderr(output), patch("radar.publish.build_opener") as network:
            self.assertEqual(main([str(self.out)]), 1)
            self.assertNotIn("TOKEN_CANARY", output.getvalue())
            network.assert_not_called()


if __name__ == "__main__":
    unittest.main()
