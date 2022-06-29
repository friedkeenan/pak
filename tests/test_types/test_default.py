import abc
from pak import *


def test_defaulted():
    DefaultedInt8 = Defaulted(Int8, 1)

    assert DefaultedInt8.mro() == [DefaultedInt8, Int8, StructType, Defaulted, Type, abc.ABC, object]

    test.type_behavior(
        DefaultedInt8,

        (0, b"\x00"),
        (1, b"\x01"),
        (2, b"\x02"),

        static_size = 1,
        alignment   = 1,
        default     = 1,
    )
