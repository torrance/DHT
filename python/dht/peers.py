import datetime
from ipaddress import IPv4Address


class Peer:
    def __init__(self, address: IPv4Address, port: int):
        self.address = address
        self.port = port
        self.last_seen = datetime.datetime.now(datetime.UTC)

    def __eq__(self, other) -> bool:
        return self.address == other.address and self.port == other.port

    def seen(self) -> None:
        self.last_seen = datetime.datetime.now(datetime.UTC)

    def __bytes__(self) -> bytes:
        return self.address.packed + self.port.to_bytes(2, "big")

    @classmethod
    def from_bytes(cls, bs: bytes) -> "Peer":
        assert len(bs) == 6
        address = IPv4Address(bs[:4])
        port = int.from_bytes(bs[4:], "big")
        return cls(address, port)


class PeerTable:
    def __init__(self):
        self.torrents = dict()

    def add(self, info_hash: int, newpeer: Peer) -> None:
        peers = self.torrents.setdefault(info_hash, [])

        # Check if the peer exists; if so, update its time
        for peer in peers:
            if peer == newpeer:
                peer.seen()
                break
        else:
            # Otherwise, add it to the list
            peers.append(newpeer)

    def get(self, info_hash) -> list[Peer]:
        peers = self.torrents.get(info_hash, [])

        # Short circuit return if peers is empty
        if not peers:
            return peers

        # Filter the list for old peers
        expiry = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)
        peers = list(filter(lambda p: p.last_seen > expiry, peers))

        # Save the filtered list
        if peers:
            self.torrents[info_hash] = peers
        else:
            del self.torrents[info_hash]

        return peers

    def __len__(self) -> int:
        return len(self.torrents)
