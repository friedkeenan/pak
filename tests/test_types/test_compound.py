import pak
import pytest

def test_static_compound():
    TestStaticCompound = pak.Compound(
        "TestStaticCompound",

        first  = pak.Int8,
        second = pak.Int16,
        third  = pak.StaticTerminatedString(3),
    )

    pak.test.type_behavior(
        TestStaticCompound,

        ((1, 2, "hi"), b"\x01\x02\x00hi\x00"),

        (dict(first=1, second=2, third="hi"), b"\x01\x02\x00hi\x00"),

        static_size = 6,
        default     = (0, 0, ""),
    )

    obj = TestStaticCompound.unpack(b"\x00\x00\x00aa\x00")
    assert isinstance(obj, TestStaticCompound.value_type)

    # The value type has equality with its own type.
    assert obj == obj

    # The value type has equality with tuples.
    assert obj == (0, 0, "aa")

    # The value type also has attributes.
    assert obj.first  == 0
    assert obj.second == 0
    assert obj.third  == "aa"

    # The value type is an iterable.
    # NOTE: We use 'tuple' here to
    # make sure that it's an iterable
    # with the appropriate values.
    assert tuple(obj) == (0, 0, "aa")

    # The object is mutable.
    obj.third = "bb"
    obj == (0, 0, "bb")

    class TestAttrSet(pak.Packet):
        compound: TestStaticCompound

    # Iterables get converted to the value type.
    assert isinstance(TestAttrSet(compound=(0, 0, "aa")).compound, TestStaticCompound.value_type)

    # Mappings get converted to the value type.
    assert isinstance(TestAttrSet(compound=dict(first=1, second=2, third="aa")).compound, TestStaticCompound.value_type)

    with pytest.raises(TypeError, match="unexpected keyword argument"):
        TestAttrSet(compound=dict(first=1, second=2, third="aa", fourth="bb"))

    with pytest.raises(TypeError, match="required positional argument"):
        TestAttrSet(compound=dict(first=1, third="aa"))

def test_dynamic_compound():
    TestDynamicCompound = pak.Compound(
        "TestDynamicCompound",

        first  = pak.Int8,
        second = pak.ULEB128,
        third  = pak.StaticTerminatedString(3),
    )

    pak.test.type_behavior(
        TestDynamicCompound,

        ((1, 2,   "hi"), b"\x01\x02hi\x00"),
        ((1, 128, "hi"), b"\x01\x80\x01hi\x00"),

        static_size = None,
        default     = (0, 0, ""),
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
