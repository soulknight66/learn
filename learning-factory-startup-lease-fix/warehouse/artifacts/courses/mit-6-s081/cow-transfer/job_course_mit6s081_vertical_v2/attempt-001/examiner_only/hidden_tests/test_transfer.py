from __future__ import annotations

import threading
import unittest

from shared_pages import SharedPageSystem


class HiddenTransferTests(unittest.TestCase):
    def test_fork_preserves_intentional_sharing(self) -> None:
        system = SharedPageSystem()
        system.create_process(1)
        system.create_shared("shared", b"before")
        system.map_shared(1, 1, "shared")
        system.fork(1, 2)
        system.write(2, 1, b"after!")
        self.assertEqual(system.read(1, 1, 6), b"after!")
        frame = next(iter(system.stats()["frames"].values()))
        self.assertEqual(frame["mapping_refs"], 2)

    def test_exec_and_exit_release_exactly_once(self) -> None:
        system = SharedPageSystem()
        system.create_process(1)
        system.alloc_private(1, 0, b"x")
        system.fork(1, 2)
        system.exec(1)
        self.assertEqual(system.stats()["frame_count"], 1)
        system.exit(2)
        self.assertEqual(system.stats()["frame_count"], 0)
        self.assertEqual(system.stats()["process_count"], 1)

    def test_cow_chain_does_not_leak(self) -> None:
        system = SharedPageSystem()
        system.create_process(1)
        system.alloc_private(1, 0, b"root")
        system.fork(1, 2)
        system.fork(2, 3)
        system.write(2, 0, b"two!")
        system.write(3, 0, b"tri!")
        self.assertEqual(system.read(1, 0, 4), b"root")
        self.assertEqual(system.read(2, 0, 4), b"two!")
        self.assertEqual(system.read(3, 0, 4), b"tri!")
        system.exit(1)
        system.exit(2)
        system.exit(3)
        self.assertEqual(system.stats()["frame_count"], 0)

    def test_concurrent_shared_writes_remain_valid(self) -> None:
        system = SharedPageSystem()
        system.create_shared("lanes")
        for pid in range(8):
            system.create_process(pid)
            system.map_shared(pid, 0, "lanes")

        def writer(pid: int) -> None:
            for value in range(100):
                system.write(pid, 0, bytes([value]), offset=pid)

        threads = [threading.Thread(target=writer, args=(pid,)) for pid in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(system.read(0, 0, 8), bytes([99]) * 8)
        frame = next(iter(system.stats()["frames"].values()))
        self.assertEqual(frame["mapping_refs"], 8)

    def test_invalid_operations_are_explicit(self) -> None:
        system = SharedPageSystem()
        system.create_process(1)
        with self.assertRaises(ValueError):
            system.create_process(1)
        with self.assertRaises(KeyError):
            system.read(1, 99, 1)
        with self.assertRaises(ValueError):
            system.alloc_private(1, 0, b"x" * (system.PAGE_SIZE + 1))


if __name__ == "__main__":
    unittest.main()
