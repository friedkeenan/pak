import math
import pak
import pytest

test_bool = pak.test.type_behavior_func_both(

    pak.Bool,

    (False, b"\x00"),
    (True,  b"\x01"),

    static_size = 1,
    alignment   = 1,
    default     = False,
)

test_int8 = pak.test.type_behavior_func_both(
    pak.Int8,

    (1,        b"\x01"),
    (2**7 - 1, b"\x7F"),
    (-1,       b"\xFF"),
    (-2**7,    b"\x80"),

    static_size = 1,
    alignment   = 1,
    default     = 0,
)

test_uint8 = pak.test.type_behavior_func_both(
    pak.UInt8,

    (1,        b"\x01"),
    (2**8 - 1, b"\xFF"),

    static_size = 1,
    alignment   = 1,
    default     = 0,
)

test_int16 = pak.test.type_behavior_func_both(
    pak.Int16,

    (1,         b"\x01\x00"),
    (2**15 - 1, b"\xFF\x7F"),
    (-1,        b"\xFF\xFF"),
    (-2**15,    b"\x00\x80"),

    static_size = 2,
    alignment   = 2,
    default     = 0,
)

test_uint16 = pak.test.type_behavior_func_both(
    pak.UInt16,

    (1,         b"\x01\x00"),
    (2**16 - 1, b"\xFF\xFF"),

    static_size = 2,
    alignment   = 2,
    default     = 0,
)

test_int32 = pak.test.type_behavior_func_both(
    pak.Int32,

    (1,         b"\x01\x00\x00\x00"),
    (2**31 - 1, b"\xFF\xFF\xFF\x7F"),
    (-1,        b"\xFF\xFF\xFF\xFF"),
    (-2**31,    b"\x00\x00\x00\x80"),

    static_size = 4,
    alignment   = 4,
    default     = 0,
)

test_uint32 = pak.test.type_behavior_func_both(
    pak.UInt32,

    (1,         b"\x01\x00\x00\x00"),
    (2**32 - 1, b"\xFF\xFF\xFF\xFF"),

    static_size = 4,
    alignment   = 4,
    default     = 0,
)

test_int64 = pak.test.type_behavior_func_both(
    pak.Int64,

    (1,         b"\x01\x00\x00\x00\x00\x00\x00\x00"),
    (2**63 - 1, b"\xFF\xFF\xFF\xFF\xFF\xFF\xFF\x7F"),
    (-1,        b"\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF"),
    (-2**63,    b"\x00\x00\x00\x00\x00\x00\x00\x80"),

    static_size = 8,
    alignment   = 8,
    default     = 0,
)

test_uint64 = pak.test.type_behavior_func_both(
    pak.UInt64,

    (1,         b"\x01\x00\x00\x00\x00\x00\x00\x00"),
    (2**64 - 1, b"\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF"),

    static_size = 8,
    alignment   = 8,
    default     = 0,
)

async def test_float32():
    await pak.test.type_behavior_both(
        pak.Float32,

        # Normal numbers
        (1,                      b"\x00\x00\x80\x3F"),
        (-1,                     b"\x00\x00\x80\xbf"),

        # Max/min normal numbers
        ((2 - 2**-23) * 2**127,  b"\xFF\xFF\x7F\x7F"),
        (-(2 - 2**-23) * 2**127, b"\xFF\xFF\x7F\xFF"),

        # Smallest positive normal
        (2**-126,                b"\x00\x00\x80\x00"),

        # Smallest positive subnormal
        (2**-149,                b"\x01\x00\x00\x00"),

        # Zero
        (0.0,                    b"\x00\x00\x00\x00"),
        (-0.0,                   b"\x00\x00\x00\x80"),

        # Infiniies
        (math.inf,               b"\x00\x00\x80\x7F"),
        (-math.inf,              b"\x00\x00\x80\xFF"),

        static_size = 4,
        alignment   = 4,
        default     = 0.0,
    )

    # NaN (cannot be checked with equality)
    assert math.isnan(pak.Float32.unpack(b"\x01\x00\x80\x7F"))
    assert math.isnan(await pak.Float32.unpack_async(b"\x01\x00\x80\x7F"))

async def test_float64():
    await pak.test.type_behavior_both(
        pak.Float64,

        # Normal numbers
        (1,                       b"\x00\x00\x00\x00\x00\x00\xF0\x3F"),
        (-1,                      b"\x00\x00\x00\x00\x00\x00\xF0\xBF"),

        # Max/min normal numbers
        ((2 - 2**-52) * 2**1023,  b"\xFF\xFF\xFF\xFF\xFF\xFF\xEF\x7F"),
        (-(2 - 2**-52) * 2**1023, b"\xFF\xFF\xFF\xFF\xFF\xFF\xEF\xFF"),

        # Smallest positive normal
        (2**-1022,                b"\x00\x00\x00\x00\x00\x00\x10\x00"),

        # Smallest positive subnormal
        (2**-1074,                b"\x01\x00\x00\x00\x00\x00\x00\x00"),

        # Zero
        (0.0,                     b"\x00\x00\x00\x00\x00\x00\x00\x00"),
        (-0.0,                    b"\x00\x00\x00\x00\x00\x00\x00\x80"),

        # Infinities
        (math.inf,                b"\x00\x00\x00\x00\x00\x00\xF0\x7F"),
        (-math.inf,               b"\x00\x00\x00\x00\x00\x00\xF0\xFF"),

        static_size = 8,
        alignment   = 8,
        default     = 0.0,
    )

    # NaN (cannot be checked with equality)
    assert math.isnan(pak.Float64.unpack(b"\x01\x00\x00\x00\x00\x00\xF0\x7F"))
    assert math.isnan(await pak.Float64.unpack_async(b"\x01\x00\x00\x00\x00\x00\xF0\x7F"))

test_leb128 = pak.test.type_behavior_func_both(
    pak.LEB128,

    (0,         b"\x00"),
    (1,         b"\x01"),
    (2**6 - 1,  b"\x3F"),
    (2**6,      b"\xC0\x00"),
    (2**7 - 1,  b"\xFF\x00"),
    (2**7,      b"\x80\x01"),
    (2**8 - 1,  b"\xFF\x01"),
    (2**13 - 1, b"\xFF\x3F"),
    (2**13,     b"\x80\xC0\x00"),
    (2**31 - 1, b"\xFF\xFF\xFF\xFF\x07"),
    (2**34 - 1, b"\xFF\xFF\xFF\xFF\x3F"),
    (2**69 - 1, b"\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\x3F"),

    (-1,     b"\x7F"),
    (-2**6,  b"\x40"),
    (-2**7,  b"\x80\x7F"),
    (-2**13, b"\x80\x40"),
    (-2**31, b"\x80\x80\x80\x80\x78"),
    (-2**34, b"\x80\x80\x80\x80\x40"),
    (-2**69, b"\x80\x80\x80\x80\x80\x80\x80\x80\x80\x40"),

    # This is a particular value that I ran into issues with in the wild.
    (-9998, b"\xF2\xB1\x7F"),

    static_size = None,
    default     = 0,
)

async def test_leb128_limited():
    # 5 bytes, max 35 bits.
    Limited = pak.LEB128.Limited(max_bytes=5)

    await pak.test.type_behavior_both(
        Limited,

        (0,         b"\x00"),
        (1,         b"\x01"),
        (2**6 - 1,  b"\x3F"),
        (2**6,      b"\xC0\x00"),
        (2**7 - 1,  b"\xFF\x00"),
        (2**7,      b"\x80\x01"),
        (2**8 - 1,  b"\xFF\x01"),
        (2**13 - 1, b"\xFF\x3F"),
        (2**13,     b"\x80\xC0\x00"),
        (2**31 - 1, b"\xFF\xFF\xFF\xFF\x07"),
        (2**34 - 1, b"\xFF\xFF\xFF\xFF\x3F"),

        (-1,     b"\x7F"),
        (-2**6,  b"\x40"),
        (-2**7,  b"\x80\x7F"),
        (-2**13, b"\x80\x40"),
        (-2**31, b"\x80\x80\x80\x80\x78"),
        (-2**34, b"\x80\x80\x80\x80\x40"),

        # This is a particular value that I ran into issues with in the wild.
        (-9998, b"\xF2\xB1\x7F"),

        static_size = None,
        default     = 0,
    )

    with pytest.raises(pak.MaxBytesExceededError, match=r"LEB128\.Limited\(max_bytes=5\)"):
        # Five bytes with their top bits set,
        # which should exceed the max bytes.
        Limited.unpack(b"\x80\x80\x80\x80\x80")

    with pytest.raises(pak.MaxBytesExceededError, match=r"LEB128\.Limited\(max_bytes=5\)"):
        # Five bytes with their top bits set,
        # which should exceed the max bytes.
        await Limited.unpack_async(b"\x80\x80\x80\x80\x80")

    with pytest.raises(ValueError, match="is out of the range of"):
        Limited.pack(2**34)

async def test_leb128_limited_unbounded_array():
    # An unbounded array should not suppress the error
    # of a limited 'LEB128' that exceeds its max bytes.

    with pytest.raises(pak.MaxBytesExceededError, match=r"LEB128\.Limited\(max_bytes=1\)"):
        pak.LEB128.Limited(max_bytes=1)[None].unpack(b"\x80")

    with pytest.raises(pak.MaxBytesExceededError, match=r"LEB128\.Limited\(max_bytes=1\)"):
        await pak.LEB128.Limited(max_bytes=1)[None].unpack_async(b"\x80")

test_uleb128 = pak.test.type_behavior_func_both(
    pak.ULEB128,

    (0,         b"\x00"),
    (1,         b"\x01"),
    (2**7 - 1,  b"\x7F"),
    (2**7,      b"\x80\x01"),
    (2**8 - 1,  b"\xFF\x01"),
    (2**31 - 1, b"\xFF\xFF\xFF\xFF\x07"),
    (2**32 - 1, b"\xFF\xFF\xFF\xFF\x0F"),
    (2**35 - 1, b"\xFF\xFF\xFF\xFF\x7F"),
    (2**69 - 1, b"\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\x3F"),

    static_size = None,
    default     = 0,
)

async def test_uleb128_limited():
    # 5 bytes, max 35 bits.
    Limited = pak.ULEB128.Limited(max_bytes=5)

    await pak.test.type_behavior_both(
        Limited,

        (0,         b"\x00"),
        (1,         b"\x01"),
        (2**7 - 1,  b"\x7F"),
        (2**7,      b"\x80\x01"),
        (2**8 - 1,  b"\xFF\x01"),
        (2**31 - 1, b"\xFF\xFF\xFF\xFF\x07"),
        (2**32 - 1, b"\xFF\xFF\xFF\xFF\x0F"),
        (2**35 - 1, b"\xFF\xFF\xFF\xFF\x7F"),

        static_size = None,
        default     = 0,
    )

    with pytest.raises(pak.MaxBytesExceededError, match=r"ULEB128\.Limited\(max_bytes=5\)"):
        # Five bytes with their top bits set,
        # which should exceed the max bytes.
        Limited.unpack(b"\x80\x80\x80\x80\x80")

    with pytest.raises(pak.MaxBytesExceededError, match=r"ULEB128\.Limited\(max_bytes=5\)"):
        # Five bytes with their top bits set,
        # which should exceed the max bytes.
        await Limited.unpack_async(b"\x80\x80\x80\x80\x80")

    with pytest.raises(ValueError, match="is out of the range of"):
        Limited.pack(2**35)

async def test_leb128_limited_unbounded_array():
    # An unbounded array should not suppress the error
    # of a limited 'ULEB128' that exceeds its max bytes.

    with pytest.raises(pak.MaxBytesExceededError, match=r"ULEB128\.Limited\(max_bytes=1\)"):
        pak.ULEB128.Limited(max_bytes=1)[None].unpack(b"\x80")

    with pytest.raises(pak.MaxBytesExceededError, match=r"ULEB128\.Limited\(max_bytes=1\)"):
        await pak.ULEB128.Limited(max_bytes=1)[None].unpack_async(b"\x80")

test_scaled_integer_static = pak.test.type_behavior_func_both(
    pak.ScaledInteger(pak.Int8, 2),

    (-0.5, b"\xFF"),
    (-1.0, b"\xFE"),
    (-1.5, b"\xFD"),

    (0.0, b"\x00"),

    (0.5, b"\x01"),
    (1.0, b"\x02"),
    (1.5, b"\x03"),

    static_size = 1,
    alignment   = 1,
    default     = 0.0,
)

test_scaled_integer_dynamic = pak.test.type_behavior_func_both(
    pak.ScaledInteger(pak.LEB128, 2),

    (-0.5, b"\x7F"),
    (-1.0, b"\x7E"),
    (-1.5, b"\x7D"),

    (0.0, b"\x00"),

    (0.5, b"\x01"),
    (1.0, b"\x02"),
    (1.5, b"\x03"),

    static_size = None,
    default     = 0.0,
)
