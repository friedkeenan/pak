import enum
import pytest
from pak import *

class EnumRaw(enum.Enum):
    A = 1
    B = 2

def test_static_enum():
    EnumStatic = Enum(Int8, EnumRaw)

    test.type_behavior(
        EnumStatic,

        (EnumRaw.A, b"\x01"),
        (EnumRaw.B, b"\x02"),

        static_size = 1,
        default     = EnumRaw.A,
    )

    assert EnumStatic.unpack(b"\x03") is Enum.INVALID

    assert EnumStatic.size(Enum.INVALID) == 1

    with pytest.raises(ValueError, match="invalid value"):
        EnumStatic.pack(Enum.INVALID)

def test_dynamic_enum():
    EnumDynamic = Enum(LEB128, EnumRaw)

    test.type_behavior(
        EnumDynamic,

        (EnumRaw.A, b"\x01"),
        (EnumRaw.B, b"\x02"),

        static_size = None,
        default     = EnumRaw.A,
    )

    with pytest.raises(ValueError, match="invalid value"):
        EnumDynamic.size(Enum.INVALID)
