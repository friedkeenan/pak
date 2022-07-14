import pak
import pytest

def test_static_bit_mask():
    TestStaticMask = pak.BitMask(
        "TestStaticMask",
        pak.UInt8,

        first  = 0,
        second = (1, 3),
        third  = (3, 5),
    )

    pak.test.type_behavior(
        TestStaticMask,

        ((False, 0, 0),  b"\x00"),
        ((True,  0, 0),  b"\x01"),
        ((False, 1, 0),  b"\x02"),
        ((True,  1, 0),  b"\x03"),
        ((True,  2, 0),  b"\x05"),
        ((True,  3, 0),  b"\x07"),
        ((False, 0, 1),  b"\x08"),

        static_size = 1,
        default     = (False, 0, 0),
    )

    with pytest.raises(ValueError, match="too wide for range"):
        TestStaticMask.pack((False, 4, 0))

    obj = TestStaticMask.unpack(b"\x00")

    # Value type has equality with tuples.
    assert obj == (False, 0, 0)

    # The value type also has attributes.
    assert obj.first  is False
    assert obj.second == 0
    assert obj.third  == 0

    class TestAttrSet(pak.Packet):
        bitmask: TestStaticMask

    assert isinstance(TestAttrSet(bitmask=(False, 0, 0)).bitmask, TestStaticMask.value_type)

def test_dynamic_bit_mask():
    TestDynamicMask = pak.BitMask(
        "TestDynamicMask",
        pak.ULEB128,

        first  = 0,
        second = (1, 3),
        third  = (7, 9),
    )

    pak.test.type_behavior(
        TestDynamicMask,

        ((False, 0, 0), b"\x00"),
        ((True,  0, 0), b"\x01"),
        ((False, 1, 0), b"\x02"),
        ((True,  1, 0), b"\x03"),
        ((True,  2, 0), b"\x05"),
        ((True,  3, 0), b"\x07"),
        ((False, 0, 1), b"\x80\x01"),

        static_size = None,
        default     = (False, 0, 0),
    )
