import itertools
import threading
from typing import Iterator

from dht.node import Node

class RoutingTable:
    K: int = 24

    def __init__(self, root):
        self.root: Node = root
        self.buckets: list[list[Node]] = [[] for _ in range(160)]
        self.lock = threading.RLock()

    def __iter__(self) -> Iterator[Node]:
        with self.lock:
            return [node for bucket in self.buckets for node in bucket].__iter__()

    def __len__(self) -> int:
        with self.lock:
            return sum(len(bucket) for bucket in self.buckets)

    def get_id(self, node: Node):
        dist = self.root.distance(node)
        if dist == 0:
            return 0
        else:
            return dist.bit_length() - 1

    def add(self, node: Node):
        if not (node.is_good or node.validate_id()):
            return

        with self.lock:
            bucket = self.buckets[self.get_id(node)]
            if node not in bucket:
                if len(bucket) < self.K:
                    # Always add a new node if there's capacity
                    bucket.append(node)
                else:
                    # Replace dead nodes
                    oldest = sorted(bucket, key=lambda n: n.last_seen)[0]
                    if oldest.is_dead:
                        bucket.remove(oldest)
                        bucket.append(node)


    def remove(self, node: Node):
        with self.lock:
            bucket = self.buckets[self.get_id(node)]
            bucket.remove(node)

    def get_closest(self, id) -> list[Node]:
        with self.lock:
            # # Always include ourselves in get_closest queries
            # nodes = itertools.chain(self, [self.root])
            return sorted(self, key=lambda n: id ^ n.id)[:8]

