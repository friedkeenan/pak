r""":class:`.Type`\s for numbers."""

from .. import util
from .type import Type
from .misc import StructType

__all__ = [
    "Bool",
    "Int8",
    "UInt8",
    "Int16",
    "UInt16",
    "Int32",
    "UInt32",
    "Int64",
    "UInt64",
    "Float32",
    "Float64",
    "LEB128",
    "ULEB128",
    "ScaledInteger",
]

class Bool(StructType):
    """A single byte truth-value."""

    _alignment = 1
    _default   = False

    fmt = "?"

# NOTE: We could change the integer types over to using
# 'int.from_bytes' and 'int.to_bytes' in the future
# with the only breaking change being from inheritance.
#
# However, from some rudimentary benchmarks, it seems
# that using 'StructType' gives marginally better
# performance than using the 'int' methods (I believe
# this is due to having to check that we read an
# adequate amount of data from the buffer when using
# the 'int' methods), so for now at least we will keep
# the integer types inheriting from 'StructType'.
#
# Additionally this prevents asymmetry from occurring
# between the integer types and the floating point types,
# as there is no 'float.from_bytes'.

class Int8(StructType):
    """A signed 8-bit integer."""

    _alignment = 1
    _default   = 0

    fmt = "b"

class UInt8(StructType):
    """An unsigned 8-bit integer."""

    _alignment = 1
    _default   = 0

    fmt = "B"

class Int16(StructType):
    """A signed 16-bit integer."""

    _alignment = 2
    _default   = 0

    fmt = "h"

class UInt16(StructType):
    """An unsigned 16-bit integer."""

    _alignment = 2
    _default   = 0

    fmt = "H"

class Int32(StructType):
    """A signed 32-bit integer."""

    _alignment = 4
    _default   = 0

    fmt = "i"

class UInt32(StructType):
    """An unsigned 32-bit integer."""

    _alignment = 4
    _default   = 0

    fmt = "I"

class Int64(StructType):
    """A signed 64-bit integer."""

    _alignment = 8
    _default   = 0

    fmt = "q"

class UInt64(StructType):
    """An unsigned 64-bit integer."""

    _alignment = 8
    _default   = 0

    fmt = "Q"

class Float32(StructType):
    """A 32-bit floating point value."""

    _alignment = 4
    _default   = 0.0

    fmt = "f"

class Float64(StructType):
    """A 64-bit floating point value."""

    _alignment = 8
    _default   = 0.0

    fmt = "d"

class LEB128(Type):
    """A variable length signed integer following the ``LEB128`` format."""

    _default = 0

    @classmethod
    def _unpack(cls, buf, *, ctx):
        num = 0

        bits = 0
        while True:
            byte = UInt8.unpack(buf, ctx=ctx)

            # Get the bottom 7 bits.
            value = byte & 0b01111111

            num  |= value << bits
            bits += 7

            # If the top bit is not set, return.
            if byte & 0b10000000 == 0:
                return util.to_signed(num, bits=bits)

    @classmethod
    def _pack(cls, value, *, ctx):
        data = b""

        while True:
            # Get the bottom 7 bits.
            to_write = value & 0b01111111

            value >>= 7

            last_byte = (
                # Value was positive and doesn't need to write the sign bit.
                (value == 0 and (to_write & 0b01000000) == 0) or

                # Value was negative and doesn't need to write the sign bit.
                (value == -1 and (to_write & 0b01000000) != 0)
            )

            if not last_byte:
                # Set the top bit.
                to_write |= 0b10000000

            data += UInt8.pack(to_write, ctx=ctx)

            if last_byte:
                return data

class ULEB128(Type):
    """A variable length unsigned integer following the ``LEB128`` format."""

    _default = 0

    @classmethod
    def _unpack(cls, buf, *, ctx):
        num = 0

        bits = 0
        while True:
            byte = UInt8.unpack(buf, ctx=ctx)

            # Get the bottom 7 bits.
            value = byte & 0b01111111

            num  |= value << bits
            bits += 7

            # If the top bit is not set, return.
            if byte & 0b10000000 == 0:
                return num

    @classmethod
    def _pack(cls, value, *, ctx):
        data = b""

        while True:
            # Get the bottom 7 bits.
            to_write = value & 0b01111111

            value >>= 7
            if value != 0:
                # Set the top bit.
                to_write |= 0b10000000

            data += UInt8.pack(to_write, ctx=ctx)

            if value == 0:
                return data

class ScaledInteger(Type):
    r"""A floating-point value derived from scaling an integer.

    Parameters
    ----------
    elem_type : typelike
        The underlying integer :class:`.Type`.
    divisor : :class:`int` or :class:`float`
        The divisor to use for scaling the underlying integer.

    Examples
    --------
    >>> import pak
    >>> # Make a 'ScaledInteger' that will divide the
    >>> # underlying 'Int8' value by '2'.
    >>> Scaled = pak.ScaledInteger(pak.Int8, 2)
    >>> Scaled.unpack(b"\x01") # Underlying value of '1'.
    0.5
    >>> Scaled.pack(0.5)
    b'\x01'
    """

    elem_type = None
    divisor   = None

    @classmethod
    def _size(cls, value, *, ctx):
        if value is cls.STATIC_SIZE:
            return cls.elem_type.size(ctx=ctx)

        return cls.elem_type.size(int(value * cls.divisor), ctx=ctx)

    @classmethod
    def _alignment(cls, *, ctx):
        return cls.elem_type.alignment(ctx=ctx)

    @classmethod
    def _default(cls, *, ctx):
        return cls.elem_type.default(ctx=ctx) / cls.divisor

    @classmethod
    def _unpack(cls, buf, *, ctx):
        return cls.elem_type.unpack(buf, ctx=ctx) / cls.divisor

    @classmethod
    def _pack(cls, value, *, ctx):
        return cls.elem_type.pack(int(value * cls.divisor), ctx=ctx)

    @classmethod
    @Type.prepare_types
    def _call(cls, elem_type: Type, divisor):
        return cls.make_type(
            f"{cls.__qualname__}({elem_type.__qualname__}, {divisor})",

            elem_type = elem_type,
            divisor   = divisor,
        )
