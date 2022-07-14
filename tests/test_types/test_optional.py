import pak
import pytest

def test_optional():
    TestPrefix = pak.Optional(pak.Int8, pak.Bool)
    pak.test.type_behavior(
        TestPrefix,

        (None, b"\x00"),
        (0,    b"\x01\x00"),

        static_size = None,
        default     = None,
    )

    TestEnd = pak.Optional(pak.Int8)
    pak.test.type_behavior(
        TestEnd,

        (None, b""),
        (0,    b"\x00"),

        static_size = None,
        default     = None,
    )

    TestFunction = pak.Optional(pak.Int8, "test")

    # Conveniently testing strings will
    # also test functions.
    assert TestFunction.has_function()

    class TestAttr(pak.Packet):
        test:     pak.Bool
        optional: TestFunction

    assert TestAttr(test=False).optional is None
    assert TestAttr(test=True).optional  == 0

    pak.test.packet_behavior(
        (TestAttr(test=False), b"\x00"),
        (TestAttr(test=True),  b"\x01\x00"),
    )

    ctx_false = TestAttr(test=False).type_ctx(None)
    ctx_true  = TestAttr(test=True).type_ctx(None)

    pak.test.type_behavior(
        TestFunction,

        (None, b""),

        static_size = None,
        default     = None,
        ctx         = ctx_false,
    )

    pak.test.type_behavior(
        TestFunction,

        (0, b"\x00"),

        static_size = None,
        default     = 0,
        ctx         = ctx_true,
    )
