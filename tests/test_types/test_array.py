import io
import pytest
from pak import *

def test_padding_array():
    assert Padding[2].default() is None

    buf = io.BytesIO(b"\x00\x00\x01\x00\x00")
    assert Padding[2].unpack(buf) is None
    assert buf.tell() == 2

    assert Padding[2].size() == 2

    assert Padding[Int8].unpack(buf) is None
    assert buf.tell() == 4

    with pytest.raises(NoStaticSizeError):
        Padding[Int8].size()

    buf = io.BytesIO(b"test data")
    assert Padding[None].unpack(buf) is None
    assert buf.tell() == 9

    with pytest.raises(NoStaticSizeError):
        Padding[None].size()

    class TestAttr(Packet):
        test:  Int8
        array: Padding["test"]

    assert TestAttr(test=2).array is None

    buf = io.BytesIO(b"\x02\xAA\xBB\xCC")
    p   = TestAttr.unpack(buf)
    assert p.test == 2 and p.array is None
    assert buf.tell() == 3

    ctx_len_2 = TestAttr(test=2).type_ctx(None)
    Padding["test"].size(ctx=ctx_len_2) == 2

    assert Padding[2].pack("whatever value")    == b"\x00\x00"
    assert Padding[Int8].pack("whatever value") == b"\x00"

    with pytest.raises(util.BufferOutOfDataError):
        Padding[2].unpack(b"\x00")

    with pytest.raises(util.BufferOutOfDataError):
        Padding[Int8].unpack(b"\x01")

    with pytest.raises(util.BufferOutOfDataError):
        TestAttr.unpack(b"\x01")

def test_raw_byte_array():
    assert RawByte[2].default() == b"\x00\x00"

    assert isinstance(RawByte[1].unpack(b"\x00"), bytearray)

    # Values are actually bytearrays but will still
    # have equality with bytes objects.
    test.assert_type_marshal(
        RawByte[2],

        (b"\xAA\xBB", b"\xAA\xBB"),

        static_size = 2,
    )

    test.assert_type_marshal(
        RawByte[Int8],

        (b"\xAA\xBB", b"\x02\xAA\xBB"),
        (b"",         b"\x00"),

        static_size = None,
    )

    test.assert_type_marshal(
        RawByte[None],

        (b"\xAA\xBB\xCC", b"\xAA\xBB\xCC"),

        static_size = None,
    )

    class TestAttr(Packet):
        test: Int8
        array: RawByte["test"]

    assert TestAttr(test=2).array == b"\x00\x00"

    test.assert_packet_marshal(
        (TestAttr(test=2, array=b"\x00\x01"), b"\x02\x00\x01"),
    )

    ctx_len_2 = TestAttr(test=2, array=b"\x00\x01").type_ctx(None)
    test.assert_type_marshal(
        RawByte["test"],

        (b"\x00\x01", b"\x00\x01"),

        static_size = 2,
        ctx         = ctx_len_2,
    )

    assert RawByte[2].pack(b"\xAA\xBB\xCC")          == b"\xAA\xBB"
    assert RawByte[2].pack(b"\xAA")                  == b"\xAA\x00"
    assert RawByte[Int8].unpack(b"\x02\xAA\xBB\xCC") == b"\xAA\xBB"

    with pytest.raises(util.BufferOutOfDataError):
        RawByte[2].unpack(b"\x00")

    with pytest.raises(util.BufferOutOfDataError):
        RawByte[Int8].unpack(b"\x01")

    with pytest.raises(util.BufferOutOfDataError):
        TestAttr.unpack(b"\x01")

def test_char_array():
    assert Char[2].default() == "aa"

    assert isinstance(Char[1].unpack(b"a"), str)

    test.assert_type_marshal(
        Char[2],

        ("ab", b"ab"),

        static_size = 2,
    )

    test.assert_type_marshal(
        Char[Int8],

        ("ab", b"\x02ab"),
        ("",   b"\x00"),

        static_size = None,
    )

    test.assert_type_marshal(
        Char[None],

        ("abc", b"abc"),

        static_size = None,
    )

    class TestAttr(Packet):
        test:  Int8
        array: Char["test"]

    assert TestAttr(test=2).array == "aa"

    test.assert_packet_marshal(
        (TestAttr(test=2, array="ab"), b"\x02ab"),
    )

    ctx_len_2 = TestAttr(test=2, array="ab").type_ctx(None)
    test.assert_type_marshal(
        Char["test"],

        ("ab", b"ab"),

        static_size = 2,
        ctx         = ctx_len_2,
    )

    assert Char[2].pack("abc")           == b"ab"
    assert Char[2].pack("a")             == b"aa"
    assert Char[Int8].unpack(b"\x02abc") ==  "ab"

    with pytest.raises(util.BufferOutOfDataError):
        Char[2].unpack(b"a")

    with pytest.raises(util.BufferOutOfDataError):
        Char[Int8].unpack(b"\x01")

    with pytest.raises(util.BufferOutOfDataError):
        TestAttr.unpack(b"\x01")

    Utf8Char = Char("utf-8")
    test.assert_type_marshal(
        Utf8Char[None],

        ("ab", b"ab"),

        static_size = None,
    )

def test_array():
    assert issubclass(Int8[2], Array)

    assert Int8[2].default() == [0, 0]

    test.assert_type_marshal(
        Int8[2],

        ([0, 1], b"\x00\x01"),

        static_size = 2,
    )

    test.assert_type_marshal(
        Int8[Int8],

        ([0, 1], b"\x02\x00\x01"),
        ([],     b"\x00"),

        static_size = None,
    )

    test.assert_type_marshal(
        Int8[None],

        ([0, 1, 2], b"\x00\x01\x02"),

        static_size = None,
    )

    assert Int8[2].pack([1]) == b"\x01\x00"

    # Conveniently testing string sizes will also
    # test function sizes.
    assert Int8["test"].has_size_function()

    class TestAttr(Packet):
        test:  Int8
        array: Int8["test"]

    assert TestAttr(test=2).array == [0, 0]

    test.assert_packet_marshal(
        (TestAttr(test=2, array=[0, 1]), b"\x02\x00\x01"),
    )

    ctx_len_2 = TestAttr(test=2, array=[0, 1]).type_ctx(None)
    test.assert_type_marshal(
        Int8["test"],

        ([0, 1], b"\x00\x01"),

        static_size = 2,
        ctx         = ctx_len_2,
    )

    with pytest.raises(Exception):
        Int8[2].unpack(b"\x00")

    with pytest.raises(Exception):
        Int8[Int8].unpack(b"\x01")

    with pytest.raises(Exception):
        TestAttr.unpack(b"\x01")
