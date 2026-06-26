from _hashlib import HASH
import datetime
import hashlib
from ipaddress import IPv4Address
import os


class AnnounceToken:
    def __init__(self):
        self.last_salt = os.urandom(20)
        self.salt = os.urandom(20)
        self.last_rotated = datetime.datetime.now(datetime.UTC)

    def rotate(self) -> bool:
        now: datetime.datetime = datetime.datetime.now(datetime.UTC)
        if now - self.last_rotated > datetime.timedelta(minutes=5):
            self.last_salt = self.salt
            self.salt = os.urandom(20)
            self.last_rotated = now
            return True

        return False

    def get(self, address: IPv4Address) -> bytes:
        self.rotate()
        token: HASH = hashlib.md5(self.salt)
        token.update(address.packed)
        return token.digest()

    def validate(self, address: IPv4Address, token: bytes) -> bool:
        self.rotate()

        t1 = hashlib.md5(self.salt)
        t1.update(address.packed)

        t2 = hashlib.md5(self.last_salt)
        t2.update(address.packed)

        return t1.digest() == token or t2.digest() == token
