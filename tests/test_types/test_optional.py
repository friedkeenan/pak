import pak
import pytest

def test_optional_specializations():
    assert issubclass(pak.Optional.PrefixChecked,   pak.Optional)
    assert issubclass(pak.Optional.Unchecked,       pak.Optional)
    assert issubclass(pak.Optional.FunctionChecked, pak.Optional)

    assert issubclass(pak.Optional(pak.Int8, pak.Bool),       pak.Optional.PrefixChecked)
    assert issubclass(pak.Optional(pak.Int8),                 pak.Optional.Unchecked)
    assert issubclass(pak.Optional(pak.Int8, "attr"),         pak.Optional.FunctionChecked)
    assert issubclass(pak.Optional(pak.Int8, lambda p: True), pak.Optional.FunctionChecked)

async def test_optional():
    TestPrefix = pak.Optional(pak.Int8, pak.Bool)
    await pak.test.type_behavior_both(
        TestPrefix,

        (None, b"\x00"),
        (0,    b"\x01\x00"),

        static_size = None,
        default     = None,
    )

    TestUnchecked = pak.Optional(pak.Int8)
    await pak.test.type_behavior_both(
        TestUnchecked,

        (None, b""),
        (0,    b"\x00"),

        static_size = None,
        default     = None,
    )

    # NOTE: Conveniently, testing string
    # sizes will also test function checking.
    TestFunction = pak.Optional(pak.Int8, "test")

    class TestAttr(pak.Packet):
        test:     pak.Bool
        optional: TestFunction

    assert TestAttr(test=False).optional is None
    assert TestAttr(test=True).optional  == 0

    await pak.test.packet_behavior_both(
        (TestAttr(test=False), b"\x00"),
        (TestAttr(test=True),  b"\x01\x00"),
    )

    ctx_false = TestAttr(test=False).type_ctx(None)
    ctx_true  = TestAttr(test=True).type_ctx(None)

    await pak.test.type_behavior_both(
        TestFunction,

        (None, b""),

        static_size = None,
        default     = None,
        ctx         = ctx_false,
    )

    await pak.test.type_behavior_both(
        TestFunction,

        (0, b"\x00"),

        static_size = None,
        default     = 0,
        ctx         = ctx_true,
    )

async def test_unchecked_optional_raises_base_exception():
    # By default, unchecked optionals try to read and just
    # pass if an exception occurs. This test ensures that
    # "system" exceptions which do not inherit from 'Exception'
    # will not be swallowed up.

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
        pak.Optional(RaisesNotAnError).unpack(b"")

    with pytest.raises(NotAnError):
        await pak.Optional(RaisesNotAnError).unpack_async(b"")

async def test_unchecked_optional_raises_unpack_not_implemented():
    # By default, unchecked optionals try to read and just
    # pass if an exception occurs. This test ensures that
    # errors due to an unpack method not being implemented
    # will not be swallowed up.

    with pytest.raises(pak.UnpackMethodNotImplementedError, match="'_unpack'"):
        pak.Optional(pak.Type).unpack(b"")

    with pytest.raises(pak.UnpackMethodNotImplementedError, match="'_unpack_async'"):
        await pak.Optional(pak.Type).unpack_async(b"")
