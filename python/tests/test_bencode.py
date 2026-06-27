import unittest

from dht.bencode import (
    BencodeException,
    decode,
    decode_dict,
    encode,
    encode_dict,
    encode_integer,
    encode_bytes,
    encode_list,
)


class TestEncodeInteger(unittest.TestCase):
    def test_positive(self) -> None:
        self.assertEqual(encode_integer(6881), b"i6881e")

    def test_zero(self) -> None:
        self.assertEqual(encode_integer(0), b"i0e")

    def test_negative(self) -> None:
        self.assertEqual(encode_integer(-1), b"i-1e")

    def test_large(self) -> None:
        self.assertEqual(encode_integer(2**160 - 1), f"i{2**160 - 1}e".encode("ascii"))


class TestEncodeBytes(unittest.TestCase):
    def test_bytes(self) -> None:
        self.assertEqual(encode_bytes(b"hello"), b"5:hello")

    def test_empty(self) -> None:
        self.assertEqual(encode_bytes(b""), b"0:")

    def test_str_input(self) -> None:
        self.assertEqual(encode_bytes("ascii"), b"5:ascii")

    def test_raw_bytes(self) -> None:
        self.assertEqual(encode_bytes(b"\x00\xff\x01"), b"3:\x00\xff\x01")


class TestEncodeList(unittest.TestCase):
    def test_simple(self) -> None:
        self.assertEqual(encode_list([1, b"two"]), b"li1e3:twoe")

    def test_empty(self) -> None:
        self.assertEqual(encode_list([]), b"le")

    def test_nested(self) -> None:
        self.assertEqual(encode_list([[1]]), b"lli1eee")


class TestEncodeDict(unittest.TestCase):
    def test_simple(self) -> None:
        self.assertEqual(encode_dict({"a": 1}), b"d1:ai1ee")

    def test_empty(self) -> None:
        self.assertEqual(encode_dict({}), b"de")

    def test_key_ordering(self) -> None:
        result = encode_dict({"b": 1, "a": 2})
        self.assertEqual(result, b"d1:ai2e1:bi1ee")

    def test_mixed_keys(self) -> None:
        """str and bytes keys should be sortable without crashing."""
        result = encode_dict({b"b": 1, "a": 2})
        self.assertEqual(result, b"d1:ai2e1:bi1ee")

    def test_nested(self) -> None:
        result = encode_dict({"a": {"b": 1}})
        self.assertEqual(result, b"d1:ad1:bi1eee")


class TestDecodeRoundTrip(unittest.TestCase):
    def test_integer(self) -> None:
        self.assertEqual(decode(encode(42)), 42)

    def test_negative_integer(self) -> None:
        self.assertEqual(decode(encode(-7)), -7)

    def test_bytes(self) -> None:
        self.assertEqual(decode(encode(b"\xab\xcd")), b"\xab\xcd")

    def test_empty_bytes(self) -> None:
        self.assertEqual(decode(encode(b"")), b"")

    def test_list(self) -> None:
        self.assertEqual(decode(encode([1, 2, b"three"])), [1, 2, b"three"])

    def test_empty_list(self) -> None:
        self.assertEqual(decode(encode([])), [])

    def test_nested_list(self) -> None:
        self.assertEqual(decode(encode([[1]])), [[1]])

    def test_dict(self) -> None:
        orig = {"a": 1, "b": b"two"}
        self.assertEqual(decode(encode(orig)), {b"a": 1, b"b": b"two"})

    def test_empty_dict(self) -> None:
        self.assertEqual(decode(encode({})), {})

    def test_nested_dict(self) -> None:
        orig = {"a": {"b": 1}}
        self.assertEqual(decode(encode(orig)), {b"a": {b"b": 1}})

    def test_str_key_becomes_bytes_key(self) -> None:
        """str keys in dicts are encoded as bytes and decoded as bytes."""
        result = decode(encode({"k": "v"}))
        self.assertEqual(result, {b"k": b"v"})

    def test_dht_message(self) -> None:
        """Encode/decode a realistic DHT message."""
        msg = {
            "t": b"\x01\x02",
            "y": "r",
            "ip": b"\xc0\xa8\x00\x01",
            "r": {"id": b"\xab" * 20, "nodes": b""},
        }
        self.assertEqual(
            decode(encode(msg)),
            {
                b"t": b"\x01\x02",
                b"y": b"r",
                b"ip": b"\xc0\xa8\x00\x01",
                b"r": {b"id": b"\xab" * 20, b"nodes": b""},
            },
        )


class TestDecodeBytes(unittest.TestCase):
    def test_decode_bytes_input(self) -> None:
        """decode_dict should accept raw bytes."""
        result = decode_dict(b"d1:ai1ee")
        self.assertEqual(result, {b"a": 1})


class TestDecodeMalformed(unittest.TestCase):
    def test_invalid_prefix(self) -> None:
        with self.assertRaises(BencodeException):
            decode(b"x1e")

    def test_decode_dict_non_dict(self) -> None:
        with self.assertRaises(AssertionError):
            decode_dict(b"li1ee")


class TestEncodeUnsupported(unittest.TestCase):
    def test_none(self) -> None:
        with self.assertRaises(BencodeException):
            encode(None)

    def test_float(self) -> None:
        with self.assertRaises(BencodeException):
            encode(3.14)
