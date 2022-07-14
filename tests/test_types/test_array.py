import io
import pak
import pytest

def test_padding_array():
    assert pak.Padding[2].default() is None

    buf = io.BytesIO(b"\x00\x00\x01\x00\x00")
    assert pak.Padding[2].unpack(buf) is None
    assert buf.tell() == 2

    assert pak.Padding[2].size() == 2

    assert pak.Padding[pak.Int8].unpack(buf) is None
    assert buf.tell() == 4

    with pytest.raises(pak.NoStaticSizeError):
        pak.Padding[pak.Int8].size()

    buf = io.BytesIO(b"test data")
    assert pak.Padding[None].unpack(buf) is None
    assert buf.tell() == 9

    with pytest.raises(pak.NoStaticSizeError):
        pak.Padding[None].size()

    class TestAttr(pak.Packet):
        test:  pak.Int8
        array: pak.Padding["test"]

    assert TestAttr(test=2).array is None

    buf = io.BytesIO(b"\x02\xAA\xBB\xCC")
    p   = TestAttr.unpack(buf)
    assert p.test == 2 and p.array is None
    assert buf.tell() == 3

    # Test you can properly delete padding array attributes.
    del p.array

    ctx_len_2 = TestAttr(test=2).type_ctx(None)
    pak.Padding["test"].size(ctx=ctx_len_2) == 2

    assert pak.Padding[2].pack("whatever value")    == b"\x00\x00"
    assert pak.Padding[pak.Int8].pack("whatever value") == b"\x00"
    assert pak.Padding[None].pack("whatever value") == b""

    with pytest.raises(pak.util.BufferOutOfDataError):
        pak.Padding[2].unpack(b"\x00")

    with pytest.raises(pak.util.BufferOutOfDataError):
        pak.Padding[pak.Int8].unpack(b"\x01")

    with pytest.raises(pak.util.BufferOutOfDataError):
        TestAttr.unpack(b"\x01")

def test_raw_byte_array():
    assert pak.RawByte[2].default() == b"\x00\x00"

    assert isinstance(pak.RawByte[1].unpack(b"\x00"), bytearray)

    # Values are actually bytearrays but will still
    # have equality with bytes objects.
    pak.test.type_behavior(
        pak.RawByte[2],

        (b"\xAA\xBB", b"\xAA\xBB"),

        static_size = 2,
        default     = b"\x00\x00",
    )

    pak.test.type_behavior(
        pak.RawByte[pak.Int8],

        (b"\xAA\xBB", b"\x02\xAA\xBB"),
        (b"",         b"\x00"),

        static_size = None,
        default     = b"",
    )

    pak.test.type_behavior(
        pak.RawByte[None],

        (b"\xAA\xBB\xCC", b"\xAA\xBB\xCC"),

        static_size = None,
        default     = b"",
    )

    class TestAttr(pak.Packet):
        test: pak.Int8
        array: pak.RawByte["test"]

    assert TestAttr(test=2).array == b"\x00\x00"

    pak.test.packet_behavior(
        (TestAttr(test=2, array=b"\x00\x01"), b"\x02\x00\x01"),
    )

    ctx_len_2 = TestAttr(test=2, array=b"\x00\x01").type_ctx(None)
    pak.test.type_behavior(
        pak.RawByte["test"],

        (b"\x00\x01", b"\x00\x01"),

        static_size = 2,
        default     = b"\x00\x00",
        ctx         = ctx_len_2,
    )

    assert pak.RawByte[2].pack(b"\xAA\xBB\xCC")          == b"\xAA\xBB"
    assert pak.RawByte[2].pack(b"\xAA")                  == b"\xAA\x00"
    assert pak.RawByte[pak.Int8].unpack(b"\x02\xAA\xBB\xCC") == b"\xAA\xBB"

    with pytest.raises(pak.util.BufferOutOfDataError):
        pak.RawByte[2].unpack(b"\x00")

    with pytest.raises(pak.util.BufferOutOfDataError):
        pak.RawByte[pak.Int8].unpack(b"\x01")

    with pytest.raises(pak.util.BufferOutOfDataError):
        TestAttr.unpack(b"\x01")

def test_char_array():
    assert isinstance(pak.Char[1].unpack(b"a"), str)

    pak.test.type_behavior(
        pak.Char[2],

        ("ab", b"ab"),

        static_size = 2,
        alignment   = 1,
        default     = "aa",
    )

    pak.test.type_behavior(
        pak.Char[pak.Int8],

        ("ab", b"\x02ab"),
        ("",   b"\x00"),

        static_size = None,
        default     = "",
    )

    pak.test.type_behavior(
        pak.Char[None],

        ("abc", b"abc"),

        static_size = None,
        default     = "",
    )

    class TestAttr(pak.Packet):
        test:  pak.Int8
        array: pak.Char["test"]

    assert TestAttr(test=2).array == "aa"

    pak.test.packet_behavior(
        (TestAttr(test=2, array="ab"), b"\x02ab"),
    )

    ctx_len_2 = TestAttr(test=2, array="ab").type_ctx(None)
    pak.test.type_behavior(
        pak.Char["test"],

        ("ab", b"ab"),

        static_size = 2,
        alignment   = 1,
        default     = "aa",
        ctx         = ctx_len_2,
    )

    assert pak.Char[2].pack("abc")           == b"ab"
    assert pak.Char[2].pack("a")             == b"aa"
    assert pak.Char[pak.Int8].unpack(b"\x02abc") ==  "ab"

    with pytest.raises(pak.util.BufferOutOfDataError):
        pak.Char[2].unpack(b"a")

    with pytest.raises(pak.util.BufferOutOfDataError):
        pak.Char[pak.Int8].unpack(b"\x01")

    with pytest.raises(pak.util.BufferOutOfDataError):
        TestAttr.unpack(b"\x01")

    Utf8Char = pak.Char("utf-8")
    pak.test.type_behavior(
        Utf8Char[None],

        ("ab", b"ab"),

        static_size = None,
        default     = "",
    )

def test_array():
    assert issubclass(pak.Int8[2], pak.Array)

    pak.test.type_behavior(
        pak.Int8[2],

        ([0, 1], b"\x00\x01"),

        static_size = 2,
        alignment   = 1,
        default     = [0, 0],
    )

    pak.test.type_behavior(
        pak.Int8[pak.Int8],

        ([0, 1], b"\x02\x00\x01"),
        ([],     b"\x00"),

        static_size = None,
        default     = [],
    )

    pak.test.type_behavior(
        pak.Int8[None],

        ([0, 1, 2], b"\x00\x01\x02"),

        static_size = None,
        default     = [],
    )

    assert pak.Int8[2].pack([1]) == b"\x01\x00"

    # Conveniently testing string sizes will also
    # test function sizes.
    assert pak.Int8["test"].has_size_function()

    class TestAttr(pak.Packet):
        test:  pak.Int8
        array: pak.Int8["test"]

    assert TestAttr(test=2).array == [0, 0]

    # Test you can properly delete array attributes.
    p = TestAttr()
    del p.array

    pak.test.packet_behavior(
        (TestAttr(test=2, array=[0, 1]), b"\x02\x00\x01"),
    )

    ctx_len_2 = TestAttr(test=2, array=[0, 1]).type_ctx(None)
    pak.test.type_behavior(
        pak.Int8["test"],

        ([0, 1], b"\x00\x01"),

        static_size = 2,
        alignment   = 1,
        default     = [0, 0],
        ctx         = ctx_len_2,
    )

    with pytest.raises(Exception):
        pak.Int8[2].unpack(b"\x00")

    with pytest.raises(Exception):
        pak.Int8[pak.Int8].unpack(b"\x01")

    with pytest.raises(Exception):
        TestAttr.unpack(b"\x01")
