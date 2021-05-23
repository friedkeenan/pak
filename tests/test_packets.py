import pytest
from pak import *

from .util import assert_packet_marshal, assert_packet_marshal_func

def test_packet():
    class TestBasic(Packet):
        attr1: Int8
        attr2: Int16

    p = TestBasic()
    assert p.attr1 == 0 and p.attr2 == 0

    assert_packet_marshal(
        (TestBasic(attr1=0, attr2=1), b"\x00\x01\x00"),
    )

    assert TestBasic.size() == 3

    assert TestBasic(attr1=0, attr2=1) == TestBasic(attr1=0, attr2=1)
    assert TestBasic(attr1=0, attr2=1) != TestBasic(attr1=1, attr2=0)

    assert repr(TestBasic(attr1=0, attr2=1)) == "TestBasic(attr1=0, attr2=1)"

    with pytest.raises(TypeError, match="Unexpected keyword arguments"):
        TestBasic(test=0)

    class TestNoSize(Packet):
        attr: RawByte[None]

    with pytest.raises(TypeError):
        TestNoSize.size()

def test_packet_property():
    class TestProperty(Packet):
        prop: Int8

        @property
        def prop(self):
            return self._prop

        @prop.setter
        def prop(self, value):
            self._prop = int(value)

    p = TestProperty()
    assert p.prop == 0

    assert_packet_marshal(
        (TestProperty(prop=1), b"\x01"),
    )

    p = TestProperty(prop=1.5)
    assert p.prop == 1

    class TestReadOnly(Packet):
        read_only: Int8

        @property
        def read_only(self):
            return 1

    p = TestReadOnly()
    assert p.read_only == 1

    assert_packet_marshal(
        (TestReadOnly(), b"\x01"),
    )

    with pytest.raises(AttributeError):
        p.read_only = 2

    with pytest.raises(AttributeError):
        TestReadOnly(read_only=2)

def test_packet_inheritance():
    class TestParent(Packet):
        test: Int8

    class TestChildBasic(TestParent):
        pass

    class TestChildOverride(TestParent):
        other: Int8

    # Annotations will get passed down unless explicated
    assert list(TestChildBasic.enumerate_field_types())    == [("test", Int8)]
    assert list(TestChildOverride.enumerate_field_types()) == [("other", Int8)]

    assert TestChildBasic()    == TestParent()
    assert TestChildOverride() != TestParent()

def test_id():
    class TestEmpty(Packet):
        pass

    assert TestEmpty.id() is None
    assert_packet_marshal(
        (TestEmpty(), b""),
    )

    assert TestEmpty.unpack_id(b"test") is None

    class TestStaticId(Packet):
        id = 1
        _id_type = Int8

    assert TestStaticId.id()     == 1
    assert TestStaticId().pack() == b"\x01"

    assert TestStaticId.unpack_id(b"\x02") == 2

    class StringToIntDynamicValue(DynamicValue):
        _type = str

        def __init__(self, string):
            self.string = string

        def get(self, *, ctx=None):
            return int(self.string)

    class TestDynamicId(Packet):
        id = "1"
        _id_type = Int8

    assert TestDynamicId.id()     == 1
    assert TestDynamicId().pack() == b"\x01"

    assert TestDynamicId.unpack_id(b"\x02") == 2

    # Disable StringToIntDynamicValue
    StringToIntDynamicValue._type = None

def test_subclass_id():
    class Root(Packet):
        pass

    class Child1(Root):
        id = 0

    class Child2(Root):
        id = 1

    class GrandChild1(Child1):
        id = 2

    assert Root.subclass_with_id(0) is Child1
    assert Root.subclass_with_id(1) is Child2
    assert Root.subclass_with_id(2) is GrandChild1
    assert Root.subclass_with_id(3) is None

def test_generic():
    assert_packet_marshal(
        (GenericPacket(data=b"\xaa\xbb\xcc"), b"\xaa\xbb\xcc"),
    )

    generic_cls = GenericPacketWithId(1, id_type=Int8)
    assert generic_cls(data=b"test").pack() == b"\x01test"

    assert GenericPacketWithId(1, id_type=Int8) is generic_cls
