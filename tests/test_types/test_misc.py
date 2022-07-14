import io
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

def test_struct():
    # StructType also gets tested further
    # with the numeric types which inherit
    # from it.

    class TestEndian(pak.StructType):
        fmt = "H"
        endian = ">"

    pak.test.type_behavior(
        TestEndian,

        (1, b"\x00\x01"),

        static_size = 2,
        default     = pak.test.NO_DEFAULT,
    )

    class TestMultiple(pak.StructType):
        fmt = "BH"

    pak.test.type_behavior(
        TestMultiple,

        ((1, 1), b"\x01\x01\x00"),

        static_size = 3,
        default     = pak.test.NO_DEFAULT,
    )
