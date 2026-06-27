import unittest

from dht.crc32c import crc32c


class TestCrc32c(unittest.TestCase):
    """Test the CRC32C implementation for consistency and basic properties."""

    def test_empty(self) -> None:
        self.assertEqual(crc32c(b""), 0x00000000)

    def test_single_byte(self) -> None:
        self.assertEqual(crc32c(b"\x00"), 0x527D5351)

    def test_123456789(self) -> None:
        self.assertEqual(crc32c(b"123456789"), 0xE3069283)

    def test_string(self) -> None:
        self.assertEqual(
            crc32c(b"The quick brown fox jumps over the lazy dog"), 0x22620404
        )

    def test_deterministic(self) -> None:
        self.assertEqual(crc32c(b"hello"), crc32c(b"hello"))

    def test_not_zero_for_input(self) -> None:
        self.assertNotEqual(crc32c(b"data"), 0)

    def test_long_input(self) -> None:
        data = bytes(range(256)) * 10
        self.assertEqual(crc32c(data), 0x42ECEDF2)

    def test_self_consistent_with_nodeid(self) -> None:
        """CRC32C should be self-consistent: nodeid + validate_id should work."""
        from ipaddress import IPv4Address
        from dht.node import nodeid, Node

        for _ in range(5):
            nid = nodeid(IPv4Address("10.0.0.1"))
            n = Node(nid, IPv4Address("10.0.0.1"), 80)
            self.assertTrue(n.validate_id())
