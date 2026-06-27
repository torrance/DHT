from ipaddress import IPv4Address
import unittest

from dht.node import Node, nodeid


class TestNodeBasics(unittest.TestCase):
    def setUp(self) -> None:
        self.n = Node(0x1234, IPv4Address("127.0.0.1"), 6881)

    def test_id(self) -> None:
        self.assertEqual(self.n.id, 0x1234)

    def test_address(self) -> None:
        self.assertEqual(self.n.address, IPv4Address("127.0.0.1"))

    def test_port(self) -> None:
        self.assertEqual(self.n.port, 6881)

    def test_id_too_large(self) -> None:
        with self.assertRaises(AssertionError):
            Node(2**160, IPv4Address("1.2.3.4"), 80)

    def test_bytes_length(self) -> None:
        self.assertEqual(len(bytes(self.n)), 26)

    def test_bytes_roundtrip(self) -> None:
        self.assertEqual(self.n, Node.from_bytes(bytes(self.n)))

    def test_distance(self) -> None:
        n2 = Node(0x5678, IPv4Address("1.1.1.1"), 80)
        self.assertEqual(self.n.distance(n2), 0x1234 ^ 0x5678)

    def test_distance_self(self) -> None:
        self.assertEqual(self.n.distance(self.n), 0)


class TestValidateId(unittest.TestCase):
    def test_valid_nodeid_passes(self) -> None:
        nid = nodeid(IPv4Address("192.168.1.1"))
        n = Node(nid, IPv4Address("192.168.1.1"), 80)
        self.assertTrue(n.validate_id())

    def test_wrong_ip_fails(self) -> None:
        nid = nodeid(IPv4Address("192.168.1.1"))
        n = Node(nid, IPv4Address("10.0.0.1"), 80)
        self.assertFalse(n.validate_id())

    def test_random_id_fails(self) -> None:
        n = Node(42, IPv4Address("1.2.3.4"), 80)
        self.assertFalse(n.validate_id())

    def test_zero_id_fails(self) -> None:
        n = Node(0, IPv4Address("1.2.3.4"), 80)
        self.assertFalse(n.validate_id())
