import pytest
from pak import *

class StringToIntDynamicValue(DynamicValue):
    _type = str

    _enabled = False

    def __init__(self, string):
        self.string = string

    def get(self, *, ctx=None):
        return int(self.string)

class BasicPacket(Packet):
    attr1: Int8
    attr2: Int16

def test_packet():
    p = BasicPacket()
    assert p.attr1 == 0 and p.attr2 == 0

    test.packet_behavior(
        (BasicPacket(attr1=0, attr2=1), b"\x00\x01\x00"),
    )

    assert BasicPacket().size() == 3

    assert BasicPacket(attr1=0, attr2=1) == BasicPacket(attr1=0, attr2=1)
    assert BasicPacket(attr1=0, attr2=1) != BasicPacket(attr1=1, attr2=0)

    assert repr(BasicPacket(attr1=0, attr2=1)) == "BasicPacket(attr1=0, attr2=1)"

    with pytest.raises(TypeError, match="Unexpected keyword arguments"):
        BasicPacket(test=0)

def test_reserved_field():
    with pytest.raises(ReservedFieldError, match="ctx"):
        class TestReservedField(Packet):
            ctx: Int8

def test_typelike_attr():
    Type.register_typelike(int, lambda x: Int8)

    class TestTypelike(Packet):
        attr: 1

    test.packet_behavior(
        (TestTypelike(attr=5), b"\x05"),
    )

    Type.unregister_typelike(int)

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

    test.packet_behavior(
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

    test.packet_behavior(
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

    # Fields will get passed down
    assert list(TestChildBasic.enumerate_field_types())    == [("test", Int8)]
    assert list(TestChildOverride.enumerate_field_types()) == [("test", Int8), ("other", Int8)]

    assert TestChildBasic()    == TestParent()
    assert TestChildOverride() != TestParent()

    test.packet_behavior(
        (
            TestChildBasic(test=1),

            b"\x01"
        ),

        (
            TestChildOverride(test=1, other=2),

            b"\x01\x02"
        ),
    )

    with pytest.raises(DuplicateFieldError, match="test"):
        class TestDuplicateField(TestParent):
            test: Int8

def test_packet_multiple_inheritance():
    class FirstParent(Packet):
        first: Int8

    class SecondParent(Packet):
        second: Int16

    class Child(FirstParent, SecondParent):
        child: Int32

    assert list(Child.enumerate_field_types()) == [
        ("first",  Int8),
        ("second", Int16),
        ("child",  Int32),
    ]

    test.packet_behavior(
        (
            Child(first=1, second=2, child=3),

            b"\x01\x02\x00\x03\x00\x00\x00"
        ),
    )

    assert Child() != FirstParent()
    assert Child() != SecondParent()

    with pytest.raises(DuplicateFieldError, match="first"):
        class TestDuplicateFirstField(FirstParent, SecondParent):
            first: Int64

    with pytest.raises(DuplicateFieldError, match="second"):
        class TestDuplicateSecondField(FirstParent, SecondParent):
            second: Int64

    class DuplicateFirstParent(Packet):
        test: Int8

    class DuplicateSecondParent(Packet):
        test: Int16

    with pytest.raises(DuplicateFieldError, match="test"):
        class TestDuplicateFieldFromParents(DuplicateFirstParent, DuplicateSecondParent):
            pass

def test_header():
    class Test(Packet):
        class Header(Packet.Header):
            size: UInt8

        byte: Int8
        short: Int16

    test.packet_behavior(
        (Test.Header(size=3), b"\x03"),
    )

    assert Test().header() == Test.Header(size=3)

    assert Test(byte=1, short=2).pack() == b"\x03\x01\x02\x00"

    with pytest.raises(TypeError, match="fields"):
        Test.Header(Test(), size=2)

    with pytest.raises(TypeError, match="header"):
        class TestHeaderWithHeader(Packet):
            class Header(Packet.Header):
                class Header(Packet.Header):
                    pass

def test_id():
    class TestEmpty(Packet):
        pass

    assert TestEmpty.id() is None
    test.packet_behavior(
        (TestEmpty(), b""),
    )

    assert TestEmpty.Header.unpack(b"test") == Packet.Header()

    class TestStaticId(Packet):
        class Header(Packet.Header):
            id: Int8

        id = 1

    assert TestStaticId.id()     == 1
    assert TestStaticId().pack() == b"\x01"

    assert TestStaticId.Header.unpack(b"\x02") == TestStaticId.Header(id=2)

    with StringToIntDynamicValue.context():
        class TestDynamicId(Packet):
            class Header(Packet.Header):
                id: Int8

            id = "1"

        assert TestDynamicId.id()     == 1
        assert TestDynamicId().pack() == b"\x01"

        assert TestDynamicId.Header.unpack(b"\x02") == TestDynamicId.Header(id=2)

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

test_generic = test.packet_behavior_func(
    (GenericPacket(data=b"\xAA\xBB\xCC"), b"\xAA\xBB\xCC"),
)
