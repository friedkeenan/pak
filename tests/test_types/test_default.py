import abc
from pak import *


def test_defaulted():
    DefaultedInt8 = Defaulted(Int8, 1)

    assert DefaultedInt8.mro() == [DefaultedInt8, Int8, StructType, Defaulted, Type, abc.ABC, object]

    assert DefaultedInt8.default() == 1

    test.assert_type_marshal(
        DefaultedInt8,

        (0, b"\x00"),
        (1, b"\x01"),
        (2, b"\x02"),
    )
