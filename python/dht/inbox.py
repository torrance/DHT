from threading import Condition
from typing import Optional


class Inbox:
    def __init__(self):
        self.store: dict[bytes, Optional[dict]] = {}
        self.cv: Condition = Condition()

    def put(self, tid: bytes, message: dict) -> bool:
        with self.cv:
            if tid in self.store.keys():
                self.store[tid] = message
                self.cv.notify_all()
                return True
            else:
                return False

    def reserve(self, tid):
        with self.cv:
            self.store[tid] = None

    def get(self, tid: bytes) -> Optional[dict]:
        with self.cv:
            # reserve() must have been called prior to get
            assert tid in self.store.keys()
            self.cv.wait_for(lambda: self.store[tid] is not None, timeout=5)

        return self.store.pop(tid)
