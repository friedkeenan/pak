import pytest
from pak import *


def test_static_compound():
    TestStaticCompound = Compound(
        "TestStaticCompound",

        first  = Int8,
        second = Int16,
        third  = Char[2],
    )

    test.type_behavior(
        TestStaticCompound,

        ((1, 2, "hi"), b"\x01\x02\x00hi"),

        static_size = 5,
        default     = (0, 0, "aa"),
    )

    obj = TestStaticCompound.unpack(b"\x00\x00\x00aa")

    # The value type has equality with tuples.
    assert obj == (0, 0, "aa")

    # The value type also has attributes.
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

    test.type_behavior(
        TestDynamicCompound,

        ((1, 2,   "hi"), b"\x01\x02hi"),
        ((1, 128, "hi"), b"\x01\x80\x01hi"),

        static_size = None,
        default     = (0, 0, "aa"),
    )

def test_aligned_compound():
    TestAligned = AlignedCompound(
        "TestAligned",

        first  = Int16,
        second = Int32,
        third  = Int8,
    )

    test.type_behavior(
        TestAligned,

        ((1, 2, 3), b"\x01\x00\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00"),

        static_size = 12,
        alignment   = 4,
        default     = (0, 0, 0),
    )

def test_faulty_aligned_compound():
    FaultyCompound = AlignedCompound(
        "FaultyCompound",

        field = ULEB128,
    )

    with pytest.raises(TypeError, match="no alignment"):
        FaultyCompound.unpack(b"\x00")

    with pytest.raises(TypeError, match="no alignment"):
        FaultyCompound.pack((0,))
