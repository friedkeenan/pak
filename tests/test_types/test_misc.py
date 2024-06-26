import io
import struct
import pak
import pytest

def test_empty():
    assert pak.Type(None) is pak.EmptyType

    assert pak.EmptyType.default() is None

    buf = io.BytesIO(b"test")
    assert pak.EmptyType.unpack(buf) is None
    assert buf.tell() == 0

    assert pak.EmptyType.pack("whatever value") == b""

    assert pak.EmptyType.size() == 0

    class TestDescriptor(pak.Packet):
        empty: pak.EmptyType

    assert isinstance(TestDescriptor.empty, pak.EmptyType)

    p = TestDescriptor()
    p.empty = "whatever value"
    assert p.empty is None

    # Test we can still delete EmptyType fields.
    del p.empty

def test_padding():
    assert pak.Padding.default() == None

    buf = io.BytesIO(b"test")
    assert pak.Padding.unpack(buf) is None
    assert buf.tell() == 1

    assert pak.Padding.pack("whatever value") == b"\x00"

    with pytest.raises(pak.util.BufferOutOfDataError):
        pak.Padding.unpack(b"")

    assert pak.Padding.size() == 1

    class TestDescriptor(pak.Packet):
        padding: pak.Padding

    assert isinstance(TestDescriptor.padding, pak.Padding)

    p = TestDescriptor()
    p.padding = "whatever value"
    assert p.padding is None

    # Test we can still delete Padding fields.
    del p.padding

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
    pak.Padding["test"].size(None, ctx=ctx_len_2) == 2

    assert pak.Padding[2].pack(None)             == b"\x00\x00"
    assert pak.Padding[2].pack("whatever value") == b"\x00\x00"

    assert pak.Padding[pak.Int8].pack("whatever value") == b"\x00"

    assert pak.Padding[None].pack("whatever value") == b""

    with pytest.raises(pak.util.BufferOutOfDataError):
        pak.Padding[2].unpack(b"\x00")

    with pytest.raises(pak.util.BufferOutOfDataError):
        pak.Padding[pak.Int8].unpack(b"\x01")

    with pytest.raises(pak.util.BufferOutOfDataError):
        TestAttr.unpack(b"\x01")

def test_raw_byte():
    pak.test.type_behavior(
        pak.RawByte,

        (b"\xAA", b"\xAA"),

        static_size = 1,
        default     = b"\x00",
    )

    assert pak.RawByte.pack(b"\xAA\xBB") == b"\xAA"

    with pytest.raises(pak.util.BufferOutOfDataError):
        pak.RawByte.unpack(b"")

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

        static_size = None,
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

# NOTE: StructType also gets tested
# further with the numeric types which
# inherit from it.

def test_struct_endian():
    class TestStruct(pak.StructType):
        fmt = "H"

    assert TestStruct.endian == "<"
    assert TestStruct.little_endian() is TestStruct

    TestStruct_BE = TestStruct.big_endian()
    assert TestStruct_BE.endian == ">"

    TestStruct_NE = TestStruct.native_endian()
    assert TestStruct_NE.endian == "="

    assert issubclass(TestStruct_BE, TestStruct)
    assert issubclass(TestStruct_NE, TestStruct)

    assert TestStruct_BE.big_endian()    is TestStruct_BE
    assert TestStruct_NE.native_endian() is TestStruct_NE

    assert issubclass(TestStruct_BE.little_endian(), TestStruct_BE)
    assert TestStruct_BE.little_endian().endian == "<"

    pak.test.type_behavior(
        TestStruct,

        (1, b"\x01\x00"),

        static_size = 2,
        default     = pak.test.NO_DEFAULT,
    )

    pak.test.type_behavior(
        TestStruct_BE,

        (1, b"\x00\x01"),

        static_size = 2,
        default     = pak.test.NO_DEFAULT,
    )

    pak.test.type_behavior(
        TestStruct_NE,

        # NOTE: We call 'struct.pack' here so that it
        # will deal with whatever the native byte order
        # is on the machine which is running the test.
        (1, struct.pack("=H", 1)),

        static_size = 2,
        default     = pak.test.NO_DEFAULT,
    )

def test_struct_multiple():
    class TestStruct(pak.StructType):
        fmt = "BH"

    pak.test.type_behavior(
        TestStruct,

        ((1, 1), b"\x01\x01\x00"),

        static_size = 3,
        default     = pak.test.NO_DEFAULT,
    )
