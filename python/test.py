from io import BytesIO, BufferedReader
import os
import unittest

from dht import bencode


class TestBencode(unittest.TestCase):
    def test_integer(self):
        data = b"i12345e"
        self.assertEqual(bencode.decode(data), 12345)

    def test_bytes(self):
        contents = os.urandom(312)
        data = str(len(contents)).encode() + b":" + contents
        self.assertEqual(bencode.decode(data), contents)

    def test_list(self):
        data = [12389, b"hi there", [54321, b"bye now"]]
        bs = bencode.encode(data)

        self.assertEqual(b"li12389e8:hi thereli54321e7:bye nowee", bs)
        self.assertEqual(data, bencode.decode(bs))

    def test_roundtrip(self):
        data = {
            b"one": [12345, b"oh hi there", {b"three": 56}],
            b"two": 79,
        }

        bs = bencode.encode(data)
        self.assertEqual(data, bencode.decode(bs))


if __name__ == "__main__":
    unittest.main()
