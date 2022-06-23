import pytest
from pak import *


def test_static_compound():
    TestStaticCompound = Compound(
        "TestStaticCompound",

        first  = Int8,
        second = Int16,
        third  = Char[2],
    )

    # The value type has equality with tuples.
    assert TestStaticCompound.default() == (0, 0, "aa")

    test.assert_type_marshal(
        TestStaticCompound,

        ((1, 2, "hi"), b"\x01\x02\x00hi"),

        static_size = 5,
    )

    # Test attributes for good measure.
    obj = TestStaticCompound.unpack(b"\x00\x00\x00aa")

    assert obj.first  == 0
    assert obj.second == 0
    assert obj.third  == "aa"

    class TestAttrSet(Packet):
        compound: TestStaticCompound

    assert isinstance(TestAttrSet(compound=(0, 0, "aa")).compound, TestStaticCompound.value_type)

def test_dynamic_compound():
    TestDynamicCompound = Compound(
        "TestDynamicCompound",

        first  = Int8,
        second = ULEB128,
        third  = Char[2],
    )

    test.assert_type_marshal(
        TestDynamicCompound,

        ((1, 2,   "hi"), b"\x01\x02hi"),
        ((1, 128, "hi"), b"\x01\x80\x01hi"),

        static_size = None,
    )
