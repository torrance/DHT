from io import BufferedReader, BytesIO


class BencodeException(Exception):
    pass


def encode(data) -> bytes:
    if isinstance(data, int):
        return encode_integer(data)
    elif isinstance(data, bytes) or isinstance(data, str):
        return encode_bytes(data)
    elif isinstance(data, list):
        return encode_list(data)
    elif isinstance(data, dict):
        return encode_dict(data)

    raise BencodeException(f"Unable to encode type {type(data)}")


def encode_integer(i: int) -> bytes:
    """Integers are encoded as i<base10 integer>e"""

    return f"i{i}e".encode("ascii")


def encode_bytes(b: bytes | str) -> bytes:
    """Byte Strings are encoded as <length>:<contents>"""

    # For simplicity of the API we will allow str but this will
    # error if the string is not representable as acii
    if isinstance(b, str):
        b = b.encode("ascii")

    assert isinstance(b, bytes)
    return f"{len(b)}:".encode("ascii") + b


def encode_list(ls: list) -> bytes:
    """Lists are encoded as l<elements>e"""

    bs = b"l"
    for l in ls:
        bs += encode(l)

    return bs + b"e"


def encode_dict(d: dict) -> bytes:
    """Dictionaries are encoded as d<pairs>e"""

    bs = b"d"

    # Keys must be in lexigraphical order
    for key in sorted(d.keys()):
        bs += encode_bytes(key) + encode(d[key])

    return bs + b"e"


def decode(b: bytes | BufferedReader):  # -> int | Any | None:
    if isinstance(b, bytes):
        b = BufferedReader(BytesIO(b))

    c = b.peek(1)[:1].decode("ascii")

    if c == "i":
        return decode_integer(b)
    elif c.isnumeric():
        return decode_bytes(b)
    elif c == "l":
        return decode_list(b)
    elif c == "d":
        return decode_dict(b)

    raise BencodeException(f"Expected one of i,l,d or [1-9] but got: {c}")


def decode_integer(b: BufferedReader) -> int:
    """Integers are encoded as i<base10 integer>e"""

    assert b.read(1) == b"i"

    cs = b""
    while (c := b.read(1)) != b"e":
        cs += c

    return int(cs)


def decode_bytes(b: BufferedReader) -> bytes:
    """Byte Strings are encoded as <length>:<contents>"""

    # decode length component
    length = b""
    while (c := b.read(1)) != b":":
        length += c
    length = int(length)

    # Return next $length of bytes
    bs = b""
    while length - len(bs) > 0:
        # Read may return less than requested amount of bytes
        bs += b.read(length - len(bs))

    return bs


def decode_list(b: BufferedReader) -> list:
    """Lists are encoded as l<elements>e"""

    assert b.read(1) == b"l"

    ls = []
    while b.peek(1)[:1] != b"e":
        ls.append(decode(b))

    assert b.read(1) == b"e"
    return ls


def decode_dict(b: bytes | BufferedReader) -> dict:
    """Dictionaries are encoded as d<pairs>e"""
    if isinstance(b, bytes):
        b = BufferedReader(BytesIO(b))

    assert b.read(1) == b"d"

    d = dict()
    while b.peek(1)[:1] != b"e":
        key = decode_bytes(b)
        val = decode(b)
        d[key] = val

    assert b.read(1) == b"e"
    return d
