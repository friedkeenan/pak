import pak
import pytest

def test_static_compound():
    TestStaticCompound = pak.Compound(
        "TestStaticCompound",

        first  = pak.Int8,
        second = pak.Int16,
        third  = pak.Char[2],
    )

    pak.test.type_behavior(
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

    class TestAttrSet(pak.Packet):
        compound: TestStaticCompound

    assert isinstance(TestAttrSet(compound=(0, 0, "aa")).compound, TestStaticCompound.value_type)

def test_dynamic_compound():
    TestDynamicCompound = pak.Compound(
        "TestDynamicCompound",

        first  = pak.Int8,
        second = pak.ULEB128,
        third  = pak.Char[2],
    )

    pak.test.type_behavior(
        TestDynamicCompound,

        ((1, 2,   "hi"), b"\x01\x02hi"),
        ((1, 128, "hi"), b"\x01\x80\x01hi"),

        static_size = None,
        default     = (0, 0, "aa"),
    )

def test_aligned_compound():
    TestAligned = pak.AlignedCompound(
        "TestAligned",

        first  = pak.Int16,
        second = pak.Int32,
        third  = pak.Int8,
    )

    pak.test.type_behavior(
        TestAligned,

        ((1, 2, 3), b"\x01\x00\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00"),

        static_size = 12,
        alignment   = 4,
        default     = (0, 0, 0),
    )

def test_faulty_aligned_compound():
    FaultyCompound = pak.AlignedCompound(
        "FaultyCompound",

        field = pak.ULEB128,
    )

    with pytest.raises(TypeError, match="no alignment"):
        FaultyCompound.unpack(b"\x00")

    with pytest.raises(TypeError, match="no alignment"):
        FaultyCompound.pack((0,))
