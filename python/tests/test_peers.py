import datetime
from ipaddress import IPv4Address
import time
import unittest

from dht.peers import Peer, PeerTable


class TestPeer(unittest.TestCase):
    def setUp(self) -> None:
        self.p = Peer(IPv4Address("192.168.1.1"), 6881)

    def test_equality_same(self) -> None:
        p2 = Peer(IPv4Address("192.168.1.1"), 6881)
        self.assertEqual(self.p, p2)

    def test_equality_different_ip(self) -> None:
        p2 = Peer(IPv4Address("10.0.0.1"), 6881)
        self.assertNotEqual(self.p, p2)

    def test_equality_different_port(self) -> None:
        p2 = Peer(IPv4Address("192.168.1.1"), 8080)
        self.assertNotEqual(self.p, p2)

    def test_bytes_length(self) -> None:
        """Compact peer format is 4 + 2 = 6 bytes."""
        self.assertEqual(len(bytes(self.p)), 6)

    def test_bytes_roundtrip(self) -> None:
        self.assertEqual(self.p, Peer.from_bytes(bytes(self.p)))

    def test_seen_updates_timestamp(self) -> None:
        before = self.p.last_seen
        self.p.seen()
        self.assertGreaterEqual(self.p.last_seen, before)


class TestPeerTable(unittest.TestCase):
    def setUp(self) -> None:
        self.pt = PeerTable()
        self.info_hash = 0xABCD

    def test_add_and_get(self) -> None:
        p = Peer(IPv4Address("1.2.3.4"), 6881)
        self.pt.add(self.info_hash, p)
        result = self.pt.get(self.info_hash)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], p)

    def test_get_unknown_torrent(self) -> None:
        self.assertEqual(self.pt.get(0x0000), [])

    def test_add_duplicate_updates_time(self) -> None:
        p = Peer(IPv4Address("1.2.3.4"), 6881)
        self.pt.add(self.info_hash, p)
        old_time = self.pt.torrents[self.info_hash][0].last_seen
        time.sleep(0.01)
        self.pt.add(self.info_hash, p)
        new_time = self.pt.torrents[self.info_hash][0].last_seen
        self.assertGreater(new_time, old_time)

    def test_add_different_peer_same_torrent(self) -> None:
        p1 = Peer(IPv4Address("1.2.3.4"), 6881)
        p2 = Peer(IPv4Address("5.6.7.8"), 7000)
        self.pt.add(self.info_hash, p1)
        self.pt.add(self.info_hash, p2)
        result = self.pt.get(self.info_hash)
        self.assertEqual(len(result), 2)

    def test_expires_old_peers(self) -> None:
        p = Peer(IPv4Address("1.2.3.4"), 6881)
        self.pt.add(self.info_hash, p)
        # Manually expire
        self.pt.torrents[self.info_hash][0].last_seen = datetime.datetime.now(
            datetime.UTC
        ) - datetime.timedelta(hours=2)
        result = self.pt.get(self.info_hash)
        self.assertEqual(result, [])
        self.assertEqual(len(self.pt), 0)

    def test_get_does_not_mutate_when_no_expiry(self) -> None:
        p = Peer(IPv4Address("1.2.3.4"), 6881)
        self.pt.add(self.info_hash, p)
        r1 = self.pt.get(self.info_hash)
        r2 = self.pt.get(self.info_hash)
        self.assertEqual(len(r1), len(r2))
