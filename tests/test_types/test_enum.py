import enum
import pytest
from pak import *

def test_enum():
    class EnumRaw(enum.Enum):
        A = 1
        B = 2

    EnumType = Enum(Int8, EnumRaw)

    test.assert_type_marshal(
        EnumType,

        (EnumRaw.A, b"\x01"),
        (EnumRaw.B, b"\x02"),
    )

    assert EnumType.default() == EnumRaw.A

    assert EnumType.unpack(b"\x03") is Enum.INVALID

    with pytest.raises(ValueError, match="invalid value"):
        EnumType.pack(Enum.INVALID)
