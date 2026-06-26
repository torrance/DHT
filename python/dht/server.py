from concurrent.futures import ThreadPoolExecutor
import logging
from ipaddress import IPv4Address
import os
import random
import socket
from threading import Thread
import time

from dht.announcetoken import AnnounceToken
import dht.bencode as bencode
from dht.inbox import Inbox
from dht.node import Node, nodeid
from dht.routingtable import RoutingTable
from dht.peers import Peer, PeerTable
from dht.threadsafebool import ThreadsafeBool
from dht.util import flatten


logger = logging.getLogger("dht")
logger.setLevel(logging.INFO)
logger.handlers.clear()

handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter(fmt="%(asctime)s [%(threadName)s] [%(levelname)s] %(message)s")
)
logger.addHandler(handler)


class Server:
    BOOTSTRAP_SERVERS: list[tuple[str, int]] = [
        ("router.bittorrent.com", 6881),
        ("router.utorrent.com", 6881),
        ("dht.transmission.bt.com", 6881),
        ("dht.libtorrent.org", 25401),
        ("router.bitcomet.com", 6881),
        ("dht.aelitis.com", 6881),
    ]

    def __init__(self, address: IPv4Address = IPv4Address("0.0.0.0"), port=0):
        self.port = port
        self.inbox = Inbox()
        self.peertable = PeerTable()
        self.announcetoken = AnnounceToken()

        # Initialise the routing table
        self.root = Node(nodeid(address), address, port)
        self.routingtable = RoutingTable(self.root)

        # Create socket connection
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("0.0.0.0", port))  # Listen on all available interfaces
        self.socket.settimeout(4)

        # Create keeepalive signal and worker threads
        self.keepalive = ThreadsafeBool(True)
        self.listener = Thread(target=self.listen, name="Listener")
        self.listener.start()
        self.router = Thread(target=self.route, name="Router")
        self.router.start()

    def listen(self):
        try:
            while self.keepalive:
                try:
                    data, (address, port) = self.socket.recvfrom(4096)
                    address = IPv4Address(address)
                except TimeoutError:
                    continue

                try:
                    data = bencode.decode_dict(data)
                except Exception as e:
                    logger.info(
                        f"{address}:{port} didn't send a bencoded dictionary: {data}",
                        exc_info=e,
                    )
                    continue

                try:
                    tid = data[b"t"]
                except KeyError:
                    logger.info(
                        f"{address}:{port} did not include a transaction ID in its message"
                    )
                    continue

                try:
                    myip = IPv4Address(data[b"ip"][:4])
                except (IndexError, KeyError):
                    pass

                try:
                    y = data[b"y"]
                except KeyError:
                    logger.info(
                        f"{address}:{port} (tid={tid}) did not have y parameter"
                    )
                    continue

                if y == b"q":
                    try:
                        q = data[b"q"]
                        logger.info(
                            f"Received query (q={q}) from {address}:{port} (tid={tid})"
                        )
                    except KeyError:
                        logger.info("Query missing q parameter")
                        continue

                    try:
                        id = int.from_bytes(data[b"a"][b"id"], "big")
                    except Exception:
                        logger.info("Query missing id argument")
                        continue

                    # Create payload skeleton
                    payload = {
                        "t": tid,
                        "y": "r",
                        "ip": address.packed + port.to_bytes(2, "big"),
                        "r": {"id": self.root.id.to_bytes(20, "big")},
                    }

                    if q == b"ping":
                        self.socket.sendto(
                            bencode.encode(payload), (str(address), port)
                        )
                        self.routingtable.add(Node(id, address, port, seen=True))
                    elif q == b"find_node":
                        try:
                            target: int = int.from_bytes(data[b"a"][b"target"], "big")
                        except Exception:
                            logger.info(
                                "Unable to extract a.target key from find_node query"
                            )
                            continue

                        try:
                            nearest: list[Node] = self.routingtable.get_closest(target)
                            payload["r"]["nodes"] = b"".join(
                                [bytes(n) for n in nearest]
                            )

                            self.socket.sendto(
                                bencode.encode(payload), (str(address), port)
                            )
                            logger.info("Responded to find_node query")

                            self.routingtable.add(Node(id, address, port, seen=True))
                        except Exception as e:
                            logger.info(
                                "An unexpected error occurred trying to respond to find_node",
                                exc_info=e,
                            )
                    elif q == b"get_peers":
                        try:
                            info_hash: int = int.from_bytes(
                                data[b"a"][b"info_hash"], "big"
                            )
                        except Exception:
                            logger.info(
                                "Unable to extract a.info_hash key from get_peers query"
                            )
                            continue

                        try:
                            payload["r"]["token"] = self.announcetoken.get(address)

                            if peers := self.peertable.get(info_hash):
                                # Return the peers as a list of compact peer formats (6 bytes)
                                payload["r"]["values"] = b"".join(
                                    [bytes(peer) for peer in peers]
                                )
                                logger.info(
                                    f"We have this torrent! Returning peer list ({len(peers)} peer(s))"
                                )

                            else:
                                # Otherwise, we return nearest peers that we know of
                                nearest = self.routingtable.get_closest(info_hash)

                                # Concatenate 26 byte node formats together
                                payload["r"]["nodes"] = b"".join(
                                    [bytes(n) for n in nearest]
                                )

                            self.socket.sendto(
                                bencode.encode(payload), (str(address), port)
                            )
                            logger.info("Responded to get_peers query")

                            self.routingtable.add(Node(id, address, port, seen=True))
                        except Exception as e:
                            logger.info(
                                "An unexpected error occurred trying to respond to get_peers",
                                exc_info=e,
                            )
                    elif q == b"announce_peer":
                        try:
                            info_hash = int.from_bytes(data[b"a"][b"info_hash"], "big")
                            token = data[b"a"][b"token"]
                            if data[b"a"].get(b"implied_port", 0):
                                peer_port: int = port
                            else:
                                peer_port: int = int.from_bytes(
                                    data[b"a"][b"port"], "big"
                                )
                        except Exception:
                            logger.info(
                                "Unable to extract expected keys from announce query"
                            )
                            continue

                        if (
                            self.announcetoken.validate(address, token)
                            and Node(id, address, port).validate_id()
                        ):
                            # Store the peer!
                            self.peertable.add(info_hash, Peer(address, peer_port))

                            self.socket.sendto(
                                bencode.encode(payload), (str(address), port)
                            )

                            logger.info(
                                f"Announce processed. We are tracking {len(self.peertable)} torrents."
                            )

                            self.routingtable.add(Node(id, address, port, seen=True))
                        else:
                            logger.info(
                                f"{address}:{port} (tid={tid}) announced but we are ignoring request"
                            )

                    else:
                        logger.info(f"Unhandled query type: q={q}")

                elif y == b"r":
                    logger.debug(f"Received response from {address}:{port} (tid={tid})")

                    try:
                        self.inbox.put(tid, data[b"r"])
                    except KeyError:
                        logger.info("Response did not include a r-dictionary")
                elif y == b"e":
                    try:
                        code, description = data[b"e"]
                        logger.warning(
                            f"{address}:{port} (tid={tid}) sent error (code={code}): {str(description)}"
                        )
                    except Exception:
                        logger.warning(
                            f"{address}:{port} (tid={tid}) sent malformed error message"
                        )
                else:
                    logger.info(
                        f"{address}:{port} (tid={tid} sent unknown method: y={y}"
                    )
        except Exception as e:
            logger.exception("Unchaught exception in listener", exc_info=e)
            self.keepalive.set(False)

        logger.info("Listener shutting down")

    def route(self):
        try:
            logger.info("Starting router...")

            # Perform initial bootstrap
            def bootstrap(domain, port):
                try:
                    address = IPv4Address(socket.gethostbyname(domain))
                except Exception:
                    logger.info(f"Failed to resolve {domain}; skipping")
                    return

                if id := self.ping_address(address, port):
                    self.routingtable.add(Node(id, address, port, seen=True))

            with ThreadPoolExecutor() as executor:
                executor.map(
                    lambda arg: bootstrap(arg[0], arg[1]), self.BOOTSTRAP_SERVERS
                )

            logger.info(
                f"Router has bootstrap with {len(self.routingtable)} seed nodes"
            )

            # Then periodically do three things:
            # 1. Search for ourself to ensure our neighbour hood is well known
            # 2. Look for random nodes so as to refresh the routing table
            # 3. Ping known nodes
            while self.keepalive:
                # Self search
                logger.info("Starting self search")
                queried = set()
                while nearest := [
                    n
                    for n in self.routingtable.get_closest(self.root.id)
                    if n not in queried
                ]:
                    with ThreadPoolExecutor() as executor:
                        nodes: list[Node] = flatten(
                            executor.map(
                                lambda n: self.find_node(self.root.id, n), nearest
                            )
                        )
                        executor.map(self.ping_node, nodes)

                    for node in nodes:
                        # The routing table will refuse:
                        # 1. nodes with invalid ids
                        # 2. nodes with stale pings
                        self.routingtable.add(node)

                    logger.info(
                        f"Routing table contains {len(self.routingtable)} nodes"
                    )

                    # Query each node no more than once
                    queried.update(nearest)

                # Random search
                logger.info("Performing random search to refresh routing table")
                randomid = int.from_bytes(os.urandom(20), "big")
                nearest = self.routingtable.get_closest(randomid)
                with ThreadPoolExecutor() as executor:
                    nodes: list[Node] = flatten(
                        executor.map(lambda n: self.find_node(randomid, n), nearest)
                    )
                    executor.map(lambda n: self.ping_node(n), nodes)

                for node in nodes:
                    if node.is_good:
                        self.routingtable.add(node)

                logger.info(f"Routing table contains {len(self.routingtable)} nodes")

                # Ping stale nodes
                with ThreadPoolExecutor() as executor:
                    stales = [n for n in self.routingtable if n.is_stale]
                    executor.map(lambda n: self.ping_node(n), stales)

                logger.info(f"Routing table contains {len(self.routingtable)} nodes")

                time.sleep(30)
        except Exception as e:
            logger.exception("Uncaught exception in router", exc_info=e)
            self.keepalive.set(False)

        logger.info("Router is shutting down")

    def ping_node(self, node: Node):
        if id := self.ping_address(node.address, node.port):
            if node.id == id:
                node.seen()

        return id

    def ping_address(self, address, port) -> int | None:
        tid = random.randbytes(4)
        payload = {
            "t": tid,
            "y": "q",
            "q": "ping",
            "a": {"id": self.root.id.to_bytes(20, "big")},
        }

        logger.debug(f"Pinging {address}:{port}")

        self.inbox.reserve(tid)
        self.socket.sendto(bencode.encode(payload), (str(address), port))
        response = self.inbox.get(tid)

        if response:
            try:
                return int.from_bytes(response[b"id"], byteorder="big")
            except Exception:
                return None

    def find_node(self, target: int, node: Node) -> list[Node]:
        tid = random.randbytes(4)
        payload = {
            "t": tid,
            "y": "q",
            "q": "find_node",
            "a": {
                "id": self.root.id.to_bytes(20, "big"),
                "target": target.to_bytes(20, "big"),
            },
        }

        self.inbox.reserve(tid)
        self.socket.sendto(bencode.encode(payload), (str(node.address), node.port))
        response = self.inbox.get(tid)

        if response is None:
            logger.debug("{node.address}:{node.port} did not respond to find_node")
            return []

        try:
            if int.from_bytes(response[b"id"], byteorder="big") == node.id:
                node.seen()

            assert isinstance(response[b"nodes"], bytes)

            nodes = []
            for i in range(0, len(response[b"nodes"]), 26):
                compact: bytes = response[b"nodes"][i : i + 26]
                assert len(compact) == 26

                nodeid = int.from_bytes(compact[0:20], byteorder="big")
                address = IPv4Address(compact[20:24])
                port = int.from_bytes(compact[24:26], byteorder="big")
                nodes.append(Node(nodeid, address, port))

            return nodes
        except Exception:
            logger.info(f"Malformed find_node response: {response}")
            return []
