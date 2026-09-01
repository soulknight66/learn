from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from learnfactory.retained_logs import BoundedBinaryCapture


class RetainedLogTests(unittest.TestCase):
    def test_binary_capture_is_bounded_redacted_and_keeps_head_and_tail(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-retained-log-") as raw:
            target = Path(raw) / "worker.log"
            capture = BoundedBinaryCapture(512)
            capture.feed(b"HEAD password=hunter2\n" + b"x" * 2000)
            capture.feed(
                b"\nAuthorization: Bearer tail-credential\nTAIL\xff\xfe"
            )

            rendered = capture.persist_redacted(target)

            self.assertLessEqual(target.stat().st_size, 512)
            self.assertEqual(rendered, target.read_text(encoding="utf-8"))
            self.assertIn("HEAD", rendered)
            self.assertIn("TAIL", rendered)
            self.assertIn("bytes omitted from retained log", rendered)
            self.assertNotIn("hunter2", rendered)
            self.assertNotIn("tail-credential", rendered)
            self.assertIn("<redacted>", rendered)
            self.assertIn("Authorization: Bearer <redacted>", rendered)
            self.assertGreater(capture.omitted_bytes, 0)

    def test_json_shaped_secret_is_redacted_without_breaking_json_syntax(self) -> None:
        with tempfile.TemporaryDirectory(prefix="learnfactory-retained-json-") as raw:
            target = Path(raw) / "events.jsonl"
            capture = BoundedBinaryCapture(1024)
            capture.feed(b'{"token":"do-not-retain","usage":{"input_tokens":3}}\n')

            capture.persist_redacted(target)
            rendered = target.read_text(encoding="utf-8")

            self.assertEqual(
                '{"token":"<redacted>","usage":{"input_tokens":3}}\n', rendered
            )


if __name__ == "__main__":
    unittest.main()
