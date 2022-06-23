import pytest
from pak import *

def test_static_bit_mask():
    TestStaticMask = BitMask(
        "TestStaticMask",
        UInt8,

        first  = 0,
        second = (1, 3),
        third  = (3, 5),
    )

    # The value type has equality with tuples.
    assert TestStaticMask.default() == (False, 0, 0)

    test.assert_type_marshal(
        TestStaticMask,

        ((False, 0, 0),  b"\x00"),
        ((True,  0, 0),  b"\x01"),
        ((False, 1, 0),  b"\x02"),
        ((True,  1, 0),  b"\x03"),
        ((True,  2, 0),  b"\x05"),
        ((True,  3, 0),  b"\x07"),
        ((False, 0, 1),  b"\x08"),

        static_size = 1,
    )

    with pytest.raises(ValueError, match="too wide for range"):
        TestStaticMask.pack((False, 4, 0))

    # Test attributes for good measure.
    obj = TestStaticMask.unpack(b"\x00")
    assert obj.first  is False
    assert obj.second == 0
    assert obj.third  == 0

    class TestAttrSet(Packet):
        bitmask: TestStaticMask

    assert isinstance(TestAttrSet(bitmask=(False, 0, 0)).bitmask, TestStaticMask.value_type)

def test_dynamic_bit_mask():
    TestDynamicMask = BitMask(
        "TestDynamicMask",
        ULEB128,

        first  = 0,
        second = (1, 3),
        third  = (7, 9),
    )

    assert TestDynamicMask.default() == (False, 0, 0)

    test.assert_type_marshal(
        TestDynamicMask,

        ((False, 0, 0), b"\x00"),
        ((True,  0, 0), b"\x01"),
        ((False, 1, 0), b"\x02"),
        ((True,  1, 0), b"\x03"),
        ((True,  2, 0), b"\x05"),
        ((True,  3, 0), b"\x07"),
        ((False, 0, 1), b"\x80\x01"),

        static_size = None,
    )
