from ipaddress import ip_address, IPv4Address, IPv6Address
import socket

import bencode
from node import Node


class Socket:
    def __init__(self, port, timeout):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind(("", port))  # "" means listen on all available interfaces
        self.s.settimeout(timeout)

    def sendto(self, node: Node, packet: bytes):
        self.s.sendto(packet, (node.address, node.port))

    def recvfrom(self):
        packet, (address, port) = self.s.recvfrom(4096)

        # All of this assumes a well formed, bencoded packet
        # with node ID correctly specified
        try:
            packet = bencode.decode(packet)

            if isinstance(packet, dict):
                if packet[b"y"] == b"q":
                    nodeid = packet[b"a"][b"id"]
                elif packet[b"y"] == b"r":
                    nodeid = packet[b"r"][b"id"]
                else:
                    raise Exception(f"Unknown packet type (y={packet[b"y"]})")
            else:
                raise Exception("Expect packet would decode to dictionary")

            return Node(nodeid, ip_address(address), port), packet
        except Exception as e:
            raise Exception("Received malformed DHT packet") from e
