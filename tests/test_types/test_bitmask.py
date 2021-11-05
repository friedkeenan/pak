import pytest
from pak import *

from ..util import assert_type_marshal

def test_bit_mask():
    TestMask = BitMask(
        "TestMask",
        UInt8,

        first  = 0,
        second = (1, 3),
        third  = (3, 5),
    )

    # The value type has equality with tuples.
    assert TestMask.default() == (False, 0, 0)

    assert_type_marshal(
        TestMask,

        ((True,  0, 0),  b"\x01"),
        ((False, 1, 0),  b"\x02"),
        ((True,  1, 0),  b"\x03"),
        ((True,  2, 0),  b"\x05"),
        ((True,  3, 0),  b"\x07"),
        ((False, 0, 1),  b"\x08"),
    )

    with pytest.raises(ValueError, match="too wide for range"):
        TestMask.pack((False, 4, 0))

    # Test attributes for good measure.
    obj = TestMask.unpack(b"\x00")
    assert obj.first  is False
    assert obj.second == 0
    assert obj.third  == 0

    class TestAttrSet(Packet):
        bitmask: TestMask

    assert isinstance(TestAttrSet(bitmask=(False, 0, 0)).bitmask, TestMask.value_type)
