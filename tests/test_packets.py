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

test_generic = assert_packet_marshal_func(
    (GenericPacket(data=b"\xaa\xbb\xcc"), b"\xaa\xbb\xcc"),
)
