import enum
import pak
import pytest

class EnumRaw(enum.Enum):
    A = 1
    B = 2

def test_static_enum():
    EnumStatic = pak.Enum(pak.Int8, EnumRaw)

    pak.test.type_behavior(
        EnumStatic,

        (EnumRaw.A, b"\x01"),
        (EnumRaw.B, b"\x02"),

        static_size = 1,
        alignment   = 1,
        default     = EnumRaw.A,
    )

    assert EnumStatic.unpack(b"\x03") is pak.Enum.INVALID

    assert EnumStatic.size(pak.Enum.INVALID) == 1

    with pytest.raises(ValueError, match="invalid value"):
        EnumStatic.pack(pak.Enum.INVALID)

def test_dynamic_enum():
    EnumDynamic = pak.Enum(pak.LEB128, EnumRaw)

    pak.test.type_behavior(
        EnumDynamic,

        (EnumRaw.A, b"\x01"),
        (EnumRaw.B, b"\x02"),

        static_size = None,
        alignment   = None,
        default     = EnumRaw.A,
    )

    with pytest.raises(ValueError, match="invalid value"):
        EnumDynamic.size(pak.Enum.INVALID)

test_enum_or = pak.test.type_behavior_func(
    pak.EnumOr(pak.Int8, EnumRaw),

    (EnumRaw.A, b"\x01"),
    (EnumRaw.B, b"\x02"),
    (3,         b"\x03"),

    static_size = 1,
    alignment   = 1,
    default     = EnumRaw.A,
)
