import enum
import pytest
from pak import *

from ..util import assert_type_marshal

def test_enum():
    class EnumRaw(enum.Enum):
        A = 1
        B = 2

    EnumType = Enum(Int8, EnumRaw)

    assert_type_marshal(
        EnumType,

        (EnumRaw.A, b"\x01"),
        (EnumRaw.B, b"\x02"),
    )

    assert EnumType.default() == EnumRaw.A

    with pytest.raises(ValueError, match="not a valid"):
        EnumType.unpack(b"\x03")
