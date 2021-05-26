from pak import *

from ..util import assert_type_marshal

def test_compound():
    TestCompound = Compound(
        "TestCompound",

        first  = Int8,
        second = Int16,
        third  = Char[2],
    )

    # The value type has equality with tuples.
    assert TestCompound.default() == (0, 0, "aa")

    assert_type_marshal(
        TestCompound,
        ((1, 2, "hi"), b"\x01\x02\x00hi"),
    )

    # Test attributes for good measure.
    obj = TestCompound.unpack(b"\x00\x00\x00aa")
    assert obj.first  == 0
    assert obj.second == 0
    assert obj.third  == "aa"

    class TestAttrSet(Packet):
        compound: TestCompound

    assert isinstance(TestAttrSet(compound=(0, 0, "aa")).compound, TestCompound.value_type)
