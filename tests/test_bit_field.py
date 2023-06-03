import pak
import pytest

def test_bit_field_inheritance():
    class Parent(pak.BitField):
        pass

    with pytest.raises(TypeError, match="inherited"):
        class Child(Parent):
            pass

def test_bit_field_no_zero_width():
    with pytest.raises(TypeError, match="width '0'"):
        class BadWidth(pak.BitField):
            field: 0

def test_bit_field_unexpected_kwargs():
    class TestUnexpectedArg(pak.BitField):
        expected_arg: 1

    with pytest.raises(TypeError, match=r"Unexpected keyword arguments.+unexpected_arg"):
        TestUnexpectedArg(expected_arg=False, unexpected_arg=True)

def test_bit_field_attributes():
    class TestAttributes(pak.BitField):
        first:  1
        second: 2

    obj = TestAttributes()

    assert obj.first  is False
    assert obj.second == 0

def test_bit_field_equality():
    class TestEquality(pak.BitField):
        first:  1
        second: 2

    class OtherBitField(pak.BitField):
        first:  1
        second: 2

    assert TestEquality()                     == TestEquality(first=False, second=0)
    assert TestEquality(first=True, second=2) == TestEquality(first=True,  second=2)

    assert TestEquality() != OtherBitField()
    assert TestEquality() != 0

class ReprTestBitField(pak.BitField):
        first:  1
        second: 2

def test_bit_field_repr():
    assert repr(ReprTestBitField()) == "ReprTestBitField(first=False, second=0)"

def test_static_bit_field():
    class TestStatic(pak.BitField):
        first:  1
        second: 2
        third:  2

    pak.test.type_behavior(
        TestStatic.Type(pak.UInt8),

        (TestStatic(first=False, second=0, third=0), b"\x00"),
        (TestStatic(first=True,  second=0, third=0), b"\x01"),
        (TestStatic(first=False, second=1, third=0), b"\x02"),
        (TestStatic(first=True,  second=1, third=0), b"\x03"),
        (TestStatic(first=False, second=2, third=0), b"\x04"),
        (TestStatic(first=True,  second=2, third=0), b"\x05"),
        (TestStatic(first=False, second=3, third=0), b"\x06"),
        (TestStatic(first=True,  second=3, third=0), b"\x07"),
        (TestStatic(first=False, second=0, third=1), b"\x08"),

        static_size = 1,
        alignment   = 1,
        default     = TestStatic(),
    )

    with pytest.raises(ValueError, match="too wide for width"):
        TestStatic.Type(pak.UInt8).pack(TestStatic(first=False, second=4, third=0))

def test_dynamic_bit_field():
    class TestDynamic(pak.BitField):
        first:   1
        second:  2
        _unused: 4
        third:   2

    pak.test.type_behavior(
        TestDynamic.Type(pak.ULEB128),

        (TestDynamic(first=False, second=0, third=0), b"\x00"),
        (TestDynamic(first=True,  second=0, third=0), b"\x01"),
        (TestDynamic(first=False, second=1, third=0), b"\x02"),
        (TestDynamic(first=True,  second=1, third=0), b"\x03"),
        (TestDynamic(first=False, second=2, third=0), b"\x04"),
        (TestDynamic(first=True,  second=2, third=0), b"\x05"),
        (TestDynamic(first=False, second=3, third=0), b"\x06"),
        (TestDynamic(first=True,  second=3, third=0), b"\x07"),

        (TestDynamic(first=False, second=0, third=1), b"\x80\x01"),

        static_size = None,
        default     = TestDynamic(),
    )

    with pytest.raises(ValueError, match="too wide for width"):
        TestDynamic.Type(pak.ULEB128).pack(TestDynamic(first=False, second=4, third=0))
