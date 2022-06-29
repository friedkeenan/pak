import pytest
from pak import *

def test_optional():
    TestPrefix = Optional(Int8, Bool)
    test.type_behavior(
        TestPrefix,

        (None, b"\x00"),
        (0,    b"\x01\x00"),

        static_size = None,
        default     = None,
    )

    TestEnd = Optional(Int8)
    test.type_behavior(
        TestEnd,

        (None, b""),
        (0,    b"\x00"),

        static_size = None,
        default     = None,
    )

    TestFunction = Optional(Int8, "test")

    # Conveniently testing strings will
    # also test functions.
    assert TestFunction.has_function()

    class TestAttr(Packet):
        test:     Bool
        optional: TestFunction

    assert TestAttr(test=False).optional is None
    assert TestAttr(test=True).optional  == 0

    test.packet_behavior(
        (TestAttr(test=False), b"\x00"),
        (TestAttr(test=True),  b"\x01\x00"),
    )

    ctx_false = TestAttr(test=False).type_ctx(None)
    ctx_true  = TestAttr(test=True).type_ctx(None)

    test.type_behavior(
        TestFunction,

        (None, b""),

        static_size = None,
        default     = None,
        ctx         = ctx_false,
    )

    test.type_behavior(
        TestFunction,

        (0, b"\x00"),

        static_size = None,
        default     = 0,
        ctx         = ctx_true,
    )
