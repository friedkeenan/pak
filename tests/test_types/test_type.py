import pytest
from pak import *

def test_type_context():
    class MyPacketContext(PacketContext):
        def __init__(self, attr):
            self.attr = attr

    p          = Packet()
    packet_ctx = MyPacketContext("test")
    type_ctx   = p.type_ctx(packet_ctx)

    assert type_ctx.packet     is p
    assert type_ctx.packet_ctx is packet_ctx

    assert type_ctx.attr == "test"

    with pytest.raises(AttributeError):
        type_ctx.test

def test_typelike():
    assert Type(Int8) is Int8

    Type.register_typelike(int, lambda x: Int8)

    assert Type(1) is Int8

    Type.unregister_typelike(int)
    with pytest.raises(TypeError, match="is not typelike"):
        Type(1)

def test_prepare_types():
    @Type.prepare_types
    def test(x, y: Type, *args: Type, **kwargs: Type):
        assert issubclass(y, Type)
        assert all(issubclass(arg, Type) for arg in args)
        assert all(issubclass(value, Type) for value in kwargs.values())

    # Nones will be converted to EmptyType
    test(1, None, None, None, test=None, other_test=None)

def test_dynamic_size():
    class StringToIntDynamicValue(DynamicValue):
        _type = str

        def __init__(self, string):
            self.string = string

        def get(self, *, ctx=None):
            return int(self.string)

    class TestSize(Type):
        _size = "1"

    assert TestSize.size() == 1

def test_dynamic_default():
    class StringToIntDynamicValue(DynamicValue):
        _type = str

        def __init__(self, string):
            self.string = string

        def get(self, *, ctx=None):
            return int(self.string)

    class TestDefault(Type):
        _default = "1"

    assert TestDefault.default() == 1
