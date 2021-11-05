from pak import *

from ..util import assert_type_marshal, assert_packet_marshal

def test_optional():
    TestPrefix = Optional(Int8, Bool)
    assert_type_marshal(
        TestPrefix,

        (None, b"\x00"),
        (0,    b"\x01\x00"),
    )

    TestEnd = Optional(Int8)
    assert_type_marshal(
        TestEnd,

        (None, b""),
        (0,    b"\x00"),
    )

    # Conveniently testing strings will
    # also test functions.
    assert Optional(Int8, "test").has_function()

    class TestAttr(Packet):
        test:     Bool
        optional: Optional(Int8, "test")

    assert TestAttr(test=False).optional is None
    assert TestAttr(test=True).optional  == 0

    assert_packet_marshal(
        (TestAttr(test=False), b"\x00"),
        (TestAttr(test=True),  b"\x01\x00"),
    )
