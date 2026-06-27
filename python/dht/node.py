import datetime
from ipaddress import IPv4Address
from os import urandom
import threading

from dht.crc32c import crc32c


def nodeid(ipaddress: IPv4Address) -> int:
    """Create a node id that is compliant with BEP 42"""

    r = int.from_bytes(urandom(1)) & 0x7
    prefix = crc32c(((int(ipaddress) & 0x030F3FFF) | (r << 29)).to_bytes(4, "big"))
    prefix >>= 11  # We only want the top 21 bits
    # Node  is (21 bit prefix) + (136 random bits) + (3 bit seed)
    return (prefix << 139) | (int.from_bytes(urandom(17), "big") << 3) | r


class Node:
    """A threadsafe representation of a node"""

    def __init__(self, id: int, address: IPv4Address, port: int, seen=False):
        assert id.bit_length() <= 160
        self.id: int = id
        self.address: IPv4Address = address
        self.port: int = port
        self.last_seen = datetime.datetime(1900, 1, 1, tzinfo=datetime.UTC)
        self.lock = threading.RLock()

        if seen:
            self.seen()

    def __str__(self):
        return f"Node(id={self.id:049d} @ {self.address}:{self.port})"

    def __hash__(self):
        return hash((self.id, self.address, self.port))

    def __eq__(self, other):
        return (
            self.id == other.id
            and self.address == other.address
            and self.port == other.port
        )

    def __bytes__(self):
        return (
            self.id.to_bytes(20, "big")
            + self.address.packed
            + self.port.to_bytes(2, "big")
        )

    @classmethod
    def from_bytes(cls, bs: bytes) -> "Node":
        assert len(bs) == 26
        id = int.from_bytes(bs[0:20], byteorder="big")
        address = IPv4Address(bs[20:24])
        port = int.from_bytes(bs[24:26], byteorder="big")
        return cls(id, address, port)

    def validate_id(self) -> bool:
        """Check whether the nodeid and ipaddress are compliant with BEP 42"""

        r = self.id & 0x7  # r is the lower 3 bits of the last byte
        prefix = crc32c(
            ((int(self.address) & 0x030F3FFF) | (r << 29)).to_bytes(4, "big")
        )
        prefix >>= 11  # We only want the top 21 bits
        # The prefix should match the top 21 bits of the node id
        return (self.id >> 139) == prefix

    def distance(self, other: "Node") -> int:
        return self.id ^ other.id

    def seen(self):
        with self.lock:
            self.last_seen = datetime.datetime.now(datetime.UTC)

    @property
    def is_good(self) -> bool:
        with self.lock:
            return datetime.datetime.now(
                datetime.UTC
            ) - self.last_seen < datetime.timedelta(minutes=5)

    @property
    def is_stale(self) -> bool:
        with self.lock:
            return datetime.datetime.now(
                datetime.UTC
            ) - self.last_seen >= datetime.timedelta(minutes=5)

    @property
    def is_dead(self) -> bool:
        with self.lock:
            return datetime.datetime.now(
                datetime.UTC
            ) - self.last_seen > datetime.timedelta(minutes=10)
