import json
import os
import tempfile
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import runtime


class OfflineRuntimeTests(unittest.TestCase):
    def test_fallback_is_explicit(self):
        old = runtime.CHAT_LOG
        with tempfile.TemporaryDirectory() as d:
            runtime.CHAT_LOG = pathlib.Path(d) / "chat.jsonl"
            runtime.local_completion = lambda *args, **kwargs: None
            out = runtime.answer("test")
            self.assertIn("OFFLINE FALLBACK", out)
            rows = runtime.CHAT_LOG.read_text().splitlines()
            self.assertEqual(len(rows), 2)
            self.assertEqual(json.loads(rows[0])["kind"], "message")
        runtime.CHAT_LOG = old


if __name__ == "__main__":
    unittest.main()
