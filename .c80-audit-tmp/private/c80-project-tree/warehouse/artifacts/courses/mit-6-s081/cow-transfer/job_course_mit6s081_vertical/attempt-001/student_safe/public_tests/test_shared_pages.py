from __future__ import annotations

import unittest

from shared_pages import SharedPageSystem


class PublicBehaviorTests(unittest.TestCase):
    def test_private_page_becomes_copy_on_write(self) -> None:
        system = SharedPageSystem()
        system.create_process(1)
        system.alloc_private(1, 0, b"parent")
        system.fork(1, 2)
        system.write(2, 0, b"child")
        self.assertEqual(system.read(1, 0, 6), b"parent")
        self.assertEqual(system.read(2, 0, 5), b"child")

    def test_unrelated_processes_share_named_page(self) -> None:
        system = SharedPageSystem()
        system.create_process(10)
        system.create_process(20)
        system.create_shared("telemetry", b"zero")
        system.map_shared(10, 3, "telemetry")
        system.map_shared(20, 8, "telemetry")
        system.write(10, 3, b"live")
        self.assertEqual(system.read(20, 8, 4), b"live")

    def test_unlink_defers_reclamation(self) -> None:
        system = SharedPageSystem()
        system.create_process(1)
        system.create_shared("mailbox", b"message")
        system.map_shared(1, 4, "mailbox")
        system.unlink_shared("mailbox")
        self.assertEqual(system.read(1, 4, 7), b"message")
        system.unmap(1, 4)
        self.assertEqual(system.stats()["frame_count"], 0)


if __name__ == "__main__":
    unittest.main()
