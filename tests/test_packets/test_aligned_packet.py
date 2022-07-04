import pytest
from pak import *

class AlignedTest(AlignedPacket):
    first:  Int16
    second: Int32
    third:  Int8

test_aligned_packet_marshal = test.packet_behavior_func(
    (
        AlignedTest(first=1, second=2, third=3),

        b"\x01\x00\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00"
    ),
)

def test_aligned_packet_size():
    assert AlignedTest.size()   == 12
    assert AlignedTest().size() == 12

def test_faulty_aligned_packet():
    class FaultyPacket(AlignedPacket):
        field: ULEB128

    with pytest.raises(TypeError, match="no alignment"):
        FaultyPacket.unpack(b"\x00")

    with pytest.raises(TypeError, match="no alignment"):
        FaultyPacket().pack()

def test_aligned_packet_read_only():
    class TestReadOnly(AlignedPacket):
        field: Int8

        @property
        def field(self):
            return 1

    assert TestReadOnly.unpack(b"\x00").field == 1
