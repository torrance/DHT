from threading import RLock


class ThreadsafeBool:
    def __init__(self, init: bool):
        self.val: bool = init
        self.lock: RLock = RLock()

    def __bool__(self) -> bool:
        with self.lock:
            return self.val

    def set(self, val: bool) -> None:
        with self.lock:
            self.val = val
