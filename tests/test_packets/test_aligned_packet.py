import asyncio
import pak
import pytest

class AlignedTest(pak.AlignedPacket):
    first:  pak.Int16
    second: pak.Int32
    third:  pak.Int8

test_aligned_packet_marshal = pak.test.packet_behavior_func_both(
    (
        AlignedTest(first=1, second=2, third=3),

        b"\x01\x00\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00"
    ),
)

def test_aligned_packet_size():
    assert AlignedTest.size()   == 12
    assert AlignedTest().size() == 12

async def test_aligned_packet_faulty_field():
    class FaultyPacket(pak.AlignedPacket):
        field: pak.ULEB128

    with pytest.raises(TypeError, match="no alignment"):
        FaultyPacket.unpack(b"\x00")

    with pytest.raises(TypeError, match="no alignment"):
        await FaultyPacket.unpack_async(b"\x00")

    with pytest.raises(TypeError, match="no alignment"):
        FaultyPacket().pack()

async def test_aligned_packet_not_enough_padding():
    with pytest.raises(pak.util.BufferOutOfDataError, match="padding"):
        # '\xAA' and '\xBB' represent alignment padding.
        #
        # There should be one more byte of alignment
        # padding at the end of the data.
        AlignedTest.unpack(b"\x01\x00\xAA\xAA\x02\x00\x00\x00\x03\xBB\xBB")

    with pytest.raises(asyncio.IncompleteReadError):
        # '\xAA' and '\xBB' represent alignment padding.
        #
        # There should be one more byte of alignment
        # padding at the end of the data.
        await AlignedTest.unpack_async(b"\x01\x00\xAA\xAA\x02\x00\x00\x00\x03\xBB\xBB")

async def test_aligned_packet_read_only():
    class TestReadOnly(pak.AlignedPacket):
        field: pak.Int8

        @property
        def field(self):
            return 1

    assert TestReadOnly.unpack(b"\x00").field == 1
    assert (await TestReadOnly.unpack_async(b"\x00")).field == 1
