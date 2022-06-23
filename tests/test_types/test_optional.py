import pytest
from pak import *

def test_optional():
    TestPrefix = Optional(Int8, Bool)
    test.assert_type_marshal(
        TestPrefix,

        (None, b"\x00"),
        (0,    b"\x01\x00"),

        static_size = None,
    )

    TestEnd = Optional(Int8)
    test.assert_type_marshal(
        TestEnd,

        (None, b""),
        (0,    b"\x00"),

        static_size = None,
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

    test.assert_packet_marshal(
        (TestAttr(test=False), b"\x00"),
        (TestAttr(test=True),  b"\x01\x00"),
    )

    ctx_false = TestAttr(test=False).type_ctx(None)
    ctx_true  = TestAttr(test=True).type_ctx(None)

    test.assert_type_marshal(
        TestFunction,

        (None, b""),

        static_size = None,
        ctx         = ctx_false,
    )

    test.assert_type_marshal(
        TestFunction,

        (0, b"\x00"),

        static_size = None,
        ctx         = ctx_true,
    )
