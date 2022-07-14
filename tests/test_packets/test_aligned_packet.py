import pak
import pytest

class AlignedTest(pak.AlignedPacket):
    first:  pak.Int16
    second: pak.Int32
    third:  pak.Int8

test_aligned_packet_marshal = pak.test.packet_behavior_func(
    (
        AlignedTest(first=1, second=2, third=3),

        b"\x01\x00\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00"
    ),
)

def test_aligned_packet_size():
    assert AlignedTest.size()   == 12
    assert AlignedTest().size() == 12

def test_faulty_aligned_packet():
    class FaultyPacket(pak.AlignedPacket):
        field: pak.ULEB128

    with pytest.raises(TypeError, match="no alignment"):
        FaultyPacket.unpack(b"\x00")

    with pytest.raises(TypeError, match="no alignment"):
        FaultyPacket().pack()

def test_aligned_packet_read_only():
    class TestReadOnly(pak.AlignedPacket):
        field: pak.Int8

        @property
        def field(self):
            return 1

    assert TestReadOnly.unpack(b"\x00").field == 1
