import pak
import pytest

def test_array_specializations():
    assert issubclass(pak.Array.FixedSize,     pak.Array)
    assert issubclass(pak.Array.SizePrefixed,  pak.Array)
    assert issubclass(pak.Array.Unbounded,     pak.Array)
    assert issubclass(pak.Array.FunctionSized, pak.Array)

    assert issubclass(pak.Int8[2],           pak.Array.FixedSize)
    assert issubclass(pak.Int8[pak.Int8],    pak.Array.SizePrefixed)
    assert issubclass(pak.Int8[None],        pak.Array.Unbounded)
    assert issubclass(pak.Int8["attr"],      pak.Array.FunctionSized)
    assert issubclass(pak.Int8[lambda p: 1], pak.Array.FunctionSized)

async def test_array():
    await pak.test.type_behavior_both(
        pak.Int8[2],

        ([0, 1], b"\x00\x01"),

        static_size = 2,
        alignment   = 1,
        default     = [0, 0],
    )

    await pak.test.type_behavior_both(
        pak.Int8[pak.Int8],

        ([0, 1], b"\x02\x00\x01"),
        ([],     b"\x00"),

        static_size = None,
        default     = [],
    )

    # Test prefixed arrays with an
    # element type with no static size.
    await pak.test.type_behavior_both(
        pak.ULEB128[pak.Int8],

        ([0, 1], b"\x02\x00\x01"),
        ([],     b"\x00"),

        static_size = None,
        default     = [],
    )

    await pak.test.type_behavior_both(
        pak.Int8[None],

        ([0, 1, 2], b"\x00\x01\x02"),

        static_size = None,
        default     = [],
    )

    assert pak.Int8[2].pack([1]) == b"\x01\x00"

    # NOTE: Conveniently, testing string
    # sizes will also test function sizes.
    class TestAttr(pak.Packet):
        test:  pak.Int8
        array: pak.Int8["test"]

    assert TestAttr(test=2).array == [0, 0]

    # Test you can properly delete array attributes.
    p = TestAttr()
    del p.array

    await pak.test.packet_behavior_both(
        (TestAttr(test=2, array=[0, 1]), b"\x02\x00\x01"),
    )

    ctx_len_2 = TestAttr(test=2, array=[0, 1]).type_ctx(None)
    await pak.test.type_behavior_both(
        pak.Int8["test"],

        ([0, 1], b"\x00\x01"),

        static_size = None,
        default     = [0, 0],
        ctx         = ctx_len_2,
    )

    with pytest.raises(Exception):
        pak.Int8[2].unpack(b"\x00")

    with pytest.raises(Exception):
        await pak.Int8[2].unpack_async(b"\x00")

    with pytest.raises(Exception):
        pak.Int8[pak.Int8].unpack(b"\x01")

    with pytest.raises(Exception):
        await pak.Int8[pak.Int8].unpack_async(b"\x01")

    with pytest.raises(Exception):
        TestAttr.unpack(b"\x01")

    with pytest.raises(Exception):
        await TestAttr.unpack_async(b"\x01")

async def test_array_size():
    class WeirdType(pak.Type):
        @classmethod
        def _array_static_size(cls, array_size, *, ctx):
            return 0

        @classmethod
        def _array_default(cls, size, *, ctx):
            return [1]

        @classmethod
        def _array_unpack(cls, buf, size, *, ctx):
            return [1]

        @classmethod
        async def _array_unpack_async(cls, reader, size, *, ctx):
            return [1]

        @classmethod
        def _array_num_elements(cls, value, *, ctx):
            return 1

        @classmethod
        def _array_ensure_size(cls, value, size, *, ctx):
            return [1]

        @classmethod
        def _array_pack(cls, value, size, *, ctx):
            return b""

    await pak.test.type_behavior_both(
        WeirdType[2],

        ([1], b""),

        static_size = 0,
        default     = [1],
    )

    await pak.test.type_behavior_both(
        WeirdType[pak.UInt8],

        ([1], b"\x01"),

        # Technically we *could* have a static size but
        # it does not mesh well with 'Array' conceptually.
        static_size = None,
        default     = [1],
    )

def test_normal_array_no_static_size():
    # NOTE: 'pak.ULEB128' has no static size.

    # Fixed size.
    with pytest.raises(pak.NoStaticSizeError):
        pak.ULEB128[1].size()

    # Prefixed size.
    with pytest.raises(pak.NoStaticSizeError):
        pak.ULEB128[pak.UInt8].size()

    # Function size.
    with pytest.raises(pak.NoStaticSizeError):
        pak.Int8["length"].size()

    # Unbound size.
    with pytest.raises(pak.NoStaticSizeError):
        pak.ULEB128[None].size()

def test_custom_array_no_static_size():
    # Test that we will still get a size if the
    # customized array static size returns 'None'.

    class NoStaticArraySize(pak.Int8):
        @classmethod
        def _array_static_size(cls, array_size, *, ctx):
            return None

    assert NoStaticArraySize[1].size([1])        == 1
    assert NoStaticArraySize[pak.Int8].size([1]) == 2
    assert NoStaticArraySize[None].size([1])     == 1

    class TestAttr(pak.Packet):
        length: pak.Int8
        array:  NoStaticArraySize["length"]

    ctx = TestAttr(length=1, array=[1]).type_ctx(None)

    assert TestAttr.array.size([1], ctx=ctx) == 1

    class TestFunction(pak.Packet):
        array: NoStaticArraySize[lambda p: 1]

    assert TestFunction.array.size([1], ctx=ctx) == 1

async def test_unbounded_array_raises_base_exception():
    # By default, unbounded arrays read until an exception
    # is thrown by unpacking. This test ensures that "system"
    # exceptions which do not inherit from 'Exception' will
    # not be swallowed up.

    class NotAnError(BaseException):
        pass

    class RaisesNotAnError(pak.Type):
        @classmethod
        def _unpack(cls, buf, *, ctx):
            raise NotAnError

        @classmethod
        async def _unpack_async(cls, reader, *, ctx):
            raise NotAnError

    with pytest.raises(NotAnError):
        RaisesNotAnError[None].unpack(b"")

    with pytest.raises(NotAnError):
        await RaisesNotAnError[None].unpack_async(b"")

async def test_unbounded_array_raises_unpack_not_implemented():
    # By default, unbounded arrays read until and exception
    # is thrown by unpacking. This test ensures that errors
    # due to an unpack method not being implemented will not
    # be swallowed up.

    with pytest.raises(pak.UnpackMethodNotImplementedError, match="'_unpack'"):
        pak.Type[None].unpack(b"")

    with pytest.raises(pak.UnpackMethodNotImplementedError, match="'_unpack_async'"):
        await pak.Type[None].unpack_async(b"")
