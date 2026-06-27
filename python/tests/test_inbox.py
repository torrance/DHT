import threading
import unittest

from dht.inbox import Inbox


class TestInbox(unittest.TestCase):
    def setUp(self) -> None:
        self.inbox = Inbox()

    def test_reserve_and_put_and_get(self) -> None:
        tid = b"\x01\x02"
        self.inbox.reserve(tid)
        msg = {b"id": b"\xab" * 20}
        t = threading.Thread(target=self.inbox.put, args=(tid, msg))
        t.start()
        result = self.inbox.get(tid)
        t.join()
        self.assertEqual(result, msg)

    def test_put_without_reserve_fails(self) -> None:
        tid = b"\xff"
        result = self.inbox.put(tid, {b"data": 1})
        self.assertFalse(result)

    def test_put_returns_true(self) -> None:
        tid = b"\xab"
        self.inbox.reserve(tid)
        result = self.inbox.put(tid, {})
        self.assertTrue(result)

    def test_get_returns_none_on_timeout(self) -> None:
        """get should return None when no response arrives before timeout."""
        tid = b"\x00"
        self.inbox.reserve(tid)
        # Don't call put — get will block for 5s then return None
        result = self.inbox.get(tid)
        self.assertIsNone(result)

    def test_pops_on_get(self) -> None:
        """After get, the tid should no longer be in the store."""
        tid = b"\x99"
        self.inbox.reserve(tid)
        self.inbox.put(tid, {b"r": 1})
        self.inbox.get(tid)
        # Putting again should fail since tid was popped
        self.assertFalse(self.inbox.put(tid, {b"r": 2}))

    def test_multiple_tids(self) -> None:
        tids = [b"\x01", b"\x02", b"\x03"]
        for tid in tids:
            self.inbox.reserve(tid)
            self.inbox.put(tid, {b"n": tid})

        for tid in tids:
            result = self.inbox.get(tid)
            self.assertEqual(result, {b"n": tid})
