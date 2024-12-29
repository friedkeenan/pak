import asyncio
import pak
import pytest

def test_subpacket_header():
    assert pak.SubPacket.Header is pak.Packet.Header

    with pytest.raises(TypeError, match="disallowed_field"):
        class TestDisallowedHeaderField(pak.SubPacket):
            class Header(pak.SubPacket.Header):
                disallowed_field: pak.Int8

    with pytest.raises(TypeError, match="disallowed_field"):
        class TestTooManyFields(pak.SubPacket):
            class Header(pak.SubPacket.Header):
                id:               pak.Int8
                disallowed_field: pak.Int8
                size:             pak.Int8

    # The following header configurations are allowed:

    class TestSizeField(pak.SubPacket):
        class Header(pak.SubPacket.Header):
            size: pak.Int8

    class TestIDField(pak.SubPacket):
        class Header(pak.SubPacket.Header):
            id: pak.Int8

    class TestIDThenSizeFields(pak.SubPacket):
        class Header(pak.SubPacket.Header):
            id:   pak.Int8
            size: pak.Int8

    class TestSizeThenIDFields(pak.SubPacket):
        class Header(pak.SubPacket.Header):
            size: pak.Int8
            id:   pak.Int8

def test_subpacket_context():
    with pytest.raises(TypeError, match="context"):
        class TestSubPacketWithContext(pak.SubPacket):
            class Context(pak.Packet.Context):
                __hash__ = pak.Packet.Context.__hash__
                __eq__   = pak.Packet.Context.__eq__

def test_subpacket_typelike():
    assert pak.Type.is_typelike(pak.SubPacket)

    assert issubclass(pak.Type(pak.SubPacket), pak.Type)

def test_subpacket_terse_array():
    assert issubclass(pak.SubPacket[1], pak.Array)

async def test_subpacket_static():
    class TestStatic(pak.SubPacket):
        field: pak.Int8
        other: pak.Int16

    await pak.test.type_behavior_both(
        pak.Type(TestStatic),

        (TestStatic(field=1, other=2), b"\x01\x02\x00"),

        static_size = 3,
        default     = TestStatic(),
    )

async def test_subpacket_dynamic():
    class TestDynamic(pak.SubPacket):
        field: pak.LEB128
        other: pak.Int16

    await pak.test.type_behavior_both(
        pak.Type(TestDynamic),

        (TestDynamic(field=1, other=2), b"\x01\x02\x00"),

        static_size = None,
        default     = TestDynamic(),
    )

async def test_subpacket_aligned():
    class TestAligned(pak.AlignedSubPacket):
        field: pak.Int8
        other: pak.Int16

    await pak.test.type_behavior_both(
        pak.Type(TestAligned),

        (TestAligned(field=1, other=2), b"\x01\x00\x02\x00"),

        static_size = 4,
        alignment   = 2,
        default     = TestAligned(),
    )

    with pytest.raises(TypeError, match="header"):
        class BogusAlignedSubPacket(pak.AlignedSubPacket):
            class Header(pak.AlignedSubPacket.Header):
                id: pak.Int8

async def test_subpacket_sized():
    class TestSized(pak.SubPacket):
        class Header(pak.SubPacket.Header):
            size: pak.Int8

        data: pak.RawByte[None]

    class TestSizedPacket(pak.Packet):
        sized: TestSized
        after: pak.Int8

    await pak.test.packet_behavior_both(
        (TestSizedPacket(sized=TestSized(data=b"data"), after=1), b"\x04data\x01"),
    )

    class TestStaticSized(pak.SubPacket):
        class Header(pak.SubPacket.Header):
            size: pak.Int8

        field: pak.Int8

    await pak.test.type_behavior_both(
        pak.Type(TestStaticSized),

        (TestStaticSized(field=2), b"\x01\x02"),

        static_size = None,
        default     = TestStaticSized(),
    )

    with pytest.raises(pak.util.BufferOutOfDataError, match="header"):
        # The header reports 4 bytes, but can only read 3.
        pak.Type(TestSized).unpack(b"\x04" + b"\x01\x02\x03")

    with pytest.raises(asyncio.IncompleteReadError):
        # The header reports 4 bytes, but can only read 3.
        await pak.Type(TestSized).unpack_async(b"\x04" + b"\x01\x02\x03")

def test_no_available_subclass_error_inheritance():
    assert issubclass(pak.SubPacket.NoAvailableSubclassError, ValueError)
    assert issubclass(pak.SubPacket.NoAvailableSubclassError, pak.Type.UnsuppressedError)

async def test_subpacket_id():
    class TestID(pak.SubPacket):
        class Header(pak.SubPacket.Header):
            id: pak.Int8

    class TestIDFirst(TestID):
        id = 1

        first: pak.Int16

    class TestIDSecond(TestID):
        id = 2

        second: pak.PrefixedString(pak.Int8)

    await pak.test.type_behavior_both(
        pak.Type(TestID),

        (TestIDFirst(first=1),       b"\x01\x01\x00"),
        (TestIDSecond(second="abc"), b"\x02\x03abc"),

        static_size = None,
        default     = pak.test.NO_DEFAULT,
    )

    with pytest.raises(pak.SubPacket.NoAvailableSubclassError, match="Unknown ID.+: 3"):
        pak.Type(TestID).unpack(b"\x03")

    with pytest.raises(pak.SubPacket.NoAvailableSubclassError, match="Unknown ID.+: 3"):
        await pak.Type(TestID).unpack_async(b"\x03")

    class TestIDUnknown(pak.SubPacket):
        class Header(pak.SubPacket.Header):
            id: pak.Int8

        @classmethod
        def _subclass_for_unknown_id(cls, id, *, ctx):
            return cls.GenericWithID(id)

    await pak.test.type_behavior_both(
        pak.Type(TestIDUnknown),

        (TestIDUnknown.GenericWithID(1)(data=b"data"), b"\x01data"),

        static_size = None,
        default     = pak.test.NO_DEFAULT,
    )

async def test_subpacket_unknown_id_unbounded_array():
    class TestID(pak.SubPacket):
        class Header(pak.SubPacket.Header):
            id: pak.Int8

    class KnownID(TestID):
        id = 1

    # An error should be raised upon encountering an unknown ID,
    # instead of being suppressed like other exceptions.

    with pytest.raises(pak.SubPacket.NoAvailableSubclassError, match="Unknown ID.+: 2"):
        # Raw data is a known ID '1', then an unknown ID '2', then another known ID '1'.
        TestID[None].unpack(b"\x01" + b"\x02" + b"\x01")

    with pytest.raises(pak.SubPacket.NoAvailableSubclassError, match="Unknown ID.+: 2"):
        # Raw data is a known ID '1', then an unknown ID '2', then another known ID '1'.
        await TestID[None].unpack_async(b"\x01" + b"\x02" + b"\x01")
