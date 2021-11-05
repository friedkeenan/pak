import io
import pytest
from pak import *

from ..util import assert_type_marshal

def test_empty():
    assert Type(None) is EmptyType

    buf = io.BytesIO(b"test")
    assert EmptyType.unpack(buf) is None
    assert buf.tell() == 0

    assert EmptyType.pack("whatever value") == b""

def test_padding():
    buf = io.BytesIO(b"test")
    assert Padding.unpack(buf) is None
    assert buf.tell() == 1

    assert Padding.pack("whatever value") == b"\x00"

    with pytest.raises(util.BufferOutOfDataError):
        Padding.unpack(b"")

def test_raw_byte():
    assert_type_marshal(
        RawByte,
        (b"\xAA", b"\xAA"),
    )

    assert RawByte.pack(b"\xAA\xBB") == b"\xAA"

    with pytest.raises(util.BufferOutOfDataError):
        RawByte.unpack(b"")

def test_char():
    assert_type_marshal(
        Char,
        ("h", b"h"),
    )

    assert Char.pack("Hello") == b"H"

    with pytest.raises(UnicodeDecodeError, match="codec can't decode byte"):
        Char.unpack(b"\x80")

    with pytest.raises(UnicodeEncodeError, match="codec can't encode character"):
        Char.pack("\x80")

    with pytest.raises(util.BufferOutOfDataError):
        Char.unpack(b"")

    Utf8Char = Char("utf-8")
    assert_type_marshal(
        Utf8Char,

        ("h",    b"h"),
        ("\x80", b"\xC2\x80"),
    )

def test_struct():
    # StructType also gets tested further
    # with the numeric types which inherit
    # from it.

    class TestEndian(StructType):
        fmt = "H"
        endian = ">"

    assert_type_marshal(
        TestEndian,

        (1, b"\x00\x01"),
    )

    class TestMultiple(StructType):
        fmt = "BH"

    assert_type_marshal(
        TestMultiple,

        ((1, 1), b"\x01\x01\x00"),
    )
