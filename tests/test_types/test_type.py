import pak
import pytest

class StringToIntDynamicValue(pak.DynamicValue):
    _type = str

    _enabled = False

    def __init__(self, string):
        self.string = string

    def get(self, *, ctx=None):
        return int(self.string)

def test_type_context():
    class MyPacketContext(pak.Packet.Context):
        def __init__(self, attr):
            self.attr = attr

            super().__init__()

        def __hash__(self):
            return hash(self.attr)

        def __eq__(self, other):
            return self.attr == other.attr

    p          = pak.Packet()
    packet_ctx = MyPacketContext("test")
    type_ctx   = p.type_ctx(packet_ctx)

    assert type_ctx.packet     is p
    assert type_ctx.packet_ctx is packet_ctx

    assert type_ctx == p.type_ctx(packet_ctx)
    assert hash(type_ctx) == hash(p.type_ctx(packet_ctx))

    assert type_ctx != pak.Packet().type_ctx(packet_ctx)
    assert hash(type_ctx) != hash(pak.Packet().type_ctx(packet_ctx))

    # Make sure we handle objects that aren't instances of 'Type.Context'.
    assert type_ctx != 1

    assert type_ctx.attr == "test"

    with pytest.raises(AttributeError):
        type_ctx.test

    with pytest.raises(AttributeError):
        pak.Type.Context().test

    # Test that 'dir()' works correctly for 'Type.Context'.
    assert [attr for attr in dir(type_ctx)           if not attr.startswith("__")] == ["_immutable_flag", "attr", "packet", "packet_ctx"]
    assert [attr for attr in dir(pak.Type.Context()) if not attr.startswith("__")] == ["packet", "packet_ctx"]

    with pytest.raises(TypeError, match="immutable"):
        type_ctx.packet = None

def test_typelike():
    assert pak.Type.is_typelike(pak.Int8)
    assert pak.Type(pak.Int8) is pak.Int8

    pak.Type.register_typelike(int, lambda x: pak.Int8)

    assert pak.Type.is_typelike(1)
    assert pak.Type(1) is pak.Int8

    pak.Type.unregister_typelike(int)

    assert not pak.Type.is_typelike(1)
    with pytest.raises(TypeError, match="is not typelike"):
        pak.Type(1)

def test_prepare_types():
    @pak.Type.prepare_types
    def test(x, y: pak.Type, *args: pak.Type, **kwargs: pak.Type):
        assert issubclass(y, pak.Type)
        assert all(issubclass(arg, pak.Type) for arg in args)
        assert all(issubclass(value, pak.Type) for value in kwargs.values())

    # Nones will be converted to EmptyType.
    test(1, None, None, None, test=None, other_test=None)

def test_static_size():
    class TestStaticSize(pak.Type):
        _size = 4

    assert TestStaticSize.size() == 4

def test_classmethod_size():
    class TestClassmethodSize(pak.Type):
        @classmethod
        def _size(cls, value, *, ctx):
            if value is pak.Type.STATIC_SIZE:
                return None

            return value * 2;

    assert TestClassmethodSize.size(5) == 10

    with pytest.raises(pak.NoStaticSizeError, match="static size"):
        TestClassmethodSize.size()

def test_dynamic_value_size():
    with StringToIntDynamicValue.context():
        class TestSize(pak.Type):
            _size = "1"

        assert TestSize.size() == 1

def test_no_size():
    class Test(pak.EmptyType):
        _size = None

    with pytest.raises(pak.NoStaticSizeError, match="static size"):
        Test.size()

def test_static_alignment():
    class Test(pak.Type):
        _alignment = 64

    assert Test.alignment() == 64

def test_no_alignment():
    class Test(pak.Type):
        _alignment = None

    with pytest.raises(TypeError, match="alignment"):
        Test.alignment()

def test_classmethod_alignment():
    class Test(pak.Type):
        @classmethod
        def _alignment(cls, *, ctx):
            return 64

    assert Test.alignment() == 64

def test_dynamic_value_alignment():
    with StringToIntDynamicValue.context():
        class Test(pak.Type):
            _alignment = "64"

        assert Test.alignment() == 64

def test_alignment_padding():
    assert pak.Type.alignment_padding_lengths(
        pak.Int16,
        pak.Int32,
        pak.Int8,

        total_alignment = 4,
    ) == [
        2,
        0,
        3,
    ]

def test_static_default():
    class Test(pak.Type):
        _default = [1, 2, 3]

    assert Test.default() == [1, 2, 3]
    assert Test.default() is not Test._default

def test_no_default():
    class Test(pak.EmptyType):
        _default = None

    with pytest.raises(TypeError, match="default value"):
        Test.default()

def test_classmethod_default():
    SENTINEL = pak.util.UniqueSentinel()

    class Test(pak.Type):
        @classmethod
        def _default(cls, *, ctx):
            return SENTINEL

    assert Test.default() is SENTINEL

def test_dynamic_value_default():
    with StringToIntDynamicValue.context():
        class TestDefault(pak.Type):
            _default = "1"

        assert TestDefault.default() == 1

def test_unpacking_capabilities():
    class SyncOnly(pak.Type):
        @classmethod
        def _unpack(cls, buf, *, ctx):
            return 1

    class AsyncOnly(pak.Type):
        @classmethod
        def _unpack_async(cls, reader, *, ctx):
            return 1

    class SyncAndAsync(pak.Type):
        @classmethod
        def _unpack(cls, buf, *, ctx):
            return 1

        @classmethod
        def _unpack_async(cls, reader, *, ctx):
            return 1

    class DerivedSyncOnly(SyncOnly):
        pass

    class DerivedAsyncOnly(AsyncOnly):
        pass

    class DerivedSyncAndAsync(SyncAndAsync):
        pass

    assert SyncOnly.has_synchronous_unpacking()
    assert DerivedSyncOnly.has_synchronous_unpacking()
    assert not SyncOnly.has_asynchronous_unpacking()
    assert not DerivedSyncOnly.has_asynchronous_unpacking()

    assert AsyncOnly.has_asynchronous_unpacking()
    assert DerivedAsyncOnly.has_asynchronous_unpacking()
    assert not AsyncOnly.has_synchronous_unpacking()
    assert not DerivedAsyncOnly.has_synchronous_unpacking()

    assert SyncAndAsync.has_synchronous_unpacking()
    assert DerivedSyncAndAsync.has_synchronous_unpacking()
    assert SyncAndAsync.has_asynchronous_unpacking()
    assert DerivedSyncAndAsync.has_asynchronous_unpacking()

def test_cached_make_type():
    class TestCall(pak.Type):
        @classmethod
        def _call(cls):
            return cls.make_type("blah")

    assert TestCall() is TestCall()

def test_make_type_namespace():
    # 'name' and 'bases' will be included in the namespace
    # despite being the names of earlier positional parameters.
    TestType = pak.Type.make_type("TestType", name="name", bases="bases")

    assert TestType.name  == "name"
    assert TestType.bases == "bases"

async def test_not_implemented_methods():
    with pytest.raises(TypeError, match="initialized"):
        pak.Type.__init__(object())

    with pytest.raises(NotImplementedError):
        pak.Type.unpack(b"")

    with pytest.raises(NotImplementedError):
        await pak.Type.unpack_async(pak.io.ByteStreamReader(b""))

    with pytest.raises(NotImplementedError):
        pak.Type.pack(None)

    with pytest.raises(NotImplementedError):
        pak.Type._call()

    class TestNotImplementedInheritedCall(pak.Type):
        pass

    with pytest.raises(NotImplementedError):
        TestNotImplementedInheritedCall()
