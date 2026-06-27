import datetime
from ipaddress import IPv4Address
import os
import unittest

from dht.node import Node, nodeid
from dht.routingtable import RoutingTable


class TestRoutingTableBasics(unittest.TestCase):
    def setUp(self) -> None:
        root = Node(1, IPv4Address("127.0.0.1"), 80)
        self.rt = RoutingTable(root)

    def test_initial_empty(self) -> None:
        self.assertEqual(len(self.rt), 0)

    def test_iter_empty(self) -> None:
        self.assertEqual(list(self.rt), [])

    def test_add_valid_node(self) -> None:
        nid = nodeid(IPv4Address("10.0.0.1"))
        n = Node(nid, IPv4Address("10.0.0.1"), 80, seen=True)
        self.rt.add(n)
        self.assertEqual(len(self.rt), 1)

    def test_add_duplicate(self) -> None:
        nid = nodeid(IPv4Address("10.0.0.1"))
        n = Node(nid, IPv4Address("10.0.0.1"), 80, seen=True)
        self.rt.add(n)
        self.rt.add(n)
        self.assertEqual(len(self.rt), 1)

    def test_add_stale_node_rejected(self) -> None:
        nid = nodeid(IPv4Address("10.0.0.1"))
        n = Node(nid, IPv4Address("10.0.0.1"), 80)
        n.last_seen = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
            minutes=10
        )
        self.rt.add(n)
        self.assertEqual(len(self.rt), 0)

    def test_add_invalid_id_rejected(self) -> None:
        n = Node(42, IPv4Address("10.0.0.1"), 80, seen=True)
        self.rt.add(n)
        self.assertEqual(len(self.rt), 0)

    def test_remove(self) -> None:
        nid = nodeid(IPv4Address("10.0.0.1"))
        n = Node(nid, IPv4Address("10.0.0.1"), 80, seen=True)
        self.rt.add(n)
        self.assertEqual(len(self.rt), 1)
        self.rt.remove(n)
        self.assertEqual(len(self.rt), 0)

    def test_remove_nonexistent(self) -> None:
        n = Node(999, IPv4Address("1.2.3.4"), 80)
        self.rt.remove(n)
        self.assertEqual(len(self.rt), 0)

    def test_multiple_adds(self) -> None:
        for i in range(10):
            ip = IPv4Address(f"10.0.{i >> 8}.{i & 0xFF}")
            nid = nodeid(ip)
            n = Node(nid, ip, 80, seen=True)
            self.rt.add(n)
        self.assertEqual(len(self.rt), 10)


class TestBucketCapacity(unittest.TestCase):
    def setUp(self):
        root = Node(1, IPv4Address("127.0.0.1"), 80)
        self.rt = RoutingTable(root)

        self.newnode = Node(
            nodeid(IPv4Address("123.123.123.123")),
            IPv4Address("123.123.123.123"),
            12345,
            seen=True,
        )
        self.bucketid = self.rt.get_id(self.newnode)

        # Manually fill the destination bucket
        for _ in range(RoutingTable.K):
            address = IPv4Address(os.urandom(4))
            self.rt.buckets[self.bucketid].append(
                Node(nodeid(address), address, 12345, seen=True)
            )

    def test_bucket_overflow_no_dead_nodes(self) -> None:
        """When a bucket is full and all nodes are good, new nodes are rejected."""
        self.assertFalse(self.rt.add(self.newnode))
        self.assertEqual(len(self.rt), RoutingTable.K)

    def test_bucket_overflow_replaces_dead_node(self) -> None:
        """When a bucket is full with a dead node, the dead node is replaced."""
        # Make the first node dead
        self.rt.buckets[self.bucketid][0].last_seen = datetime.datetime.now(
            datetime.UTC
        ) - datetime.timedelta(minutes=11)

        self.assertTrue(self.rt.add(self.newnode))
        self.assertEqual(len(self.rt), RoutingTable.K)


class TestGetId(unittest.TestCase):
    def test_msb_bucket_index(self) -> None:
        """Bucket index is the position of the MSB of the XOR distance."""
        root = Node(1, IPv4Address("127.0.0.1"), 80)
        rt = RoutingTable(root)
        # distance(1, 0x100) = 0x101, bit_length=9, bucket=8
        n = Node(0x100, IPv4Address("1.2.3.4"), 80)
        self.assertEqual(rt.get_id(n), 8)
        # distance(1, 0x200) = 0x201, bit_length=10, bucket=9
        n2 = Node(0x200, IPv4Address("5.6.7.8"), 80)
        self.assertEqual(rt.get_id(n2), 9)
