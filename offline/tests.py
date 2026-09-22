import json
import os
import pathlib
import tempfile
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import runtime
import watermark


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

    def test_watermark_does_not_change_canonical_artifact(self):
        content = "canonical response"
        presented, meta = watermark.present(content)
        self.assertIn(content, presented)
        self.assertIn(meta["artifact_hash"][:16], presented)
        self.assertEqual(meta["association"], "PRESENTATION_ONLY")
        self.assertEqual(meta["artifact_hash"], watermark.artifact_hash(content))
        self.assertTrue(watermark.verify(content, meta))
        tampered = content + "x"
        self.assertFalse(watermark.verify(tampered, meta))
        self.assertNotEqual(presented, content)

    def test_presentation_api_keeps_canonical_and_watermark_separate(self):
        old = runtime.CHAT_LOG
        with tempfile.TemporaryDirectory() as d:
            runtime.CHAT_LOG = pathlib.Path(d) / "chat.jsonl"
            runtime.local_completion = lambda *args, **kwargs: "local answer"
            canonical = runtime.answer("hello")
            presented, meta = watermark.present(canonical)
            self.assertEqual(canonical, "local answer")
            meta_text = meta["artifact_hash"][:16]
            self.assertIn(meta_text, presented)
        runtime.CHAT_LOG = old


if __name__ == "__main__":
    unittest.main()
