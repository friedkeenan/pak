r""":class:`~.Type`\s for numbers."""

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
]

class Bool(StructType):
    """A single byte truth-value."""

    _alignment = 1
    _default   = False

    fmt = "?"

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
    """A 32-bit floating point value"""

    _alignment = 4
    _default   = 0.0

    fmt = "f"

class Float64(StructType):
    """A 64-bit floating point value"""

    _alignment = 8
    _default   = 0.0

    fmt = "d"

class LEB128(Type):
    """A variable length signed integer following the ``LEB128`` format."""

    _default = 0

    # TODO: See if there's a way to calculate the size of a packed LEB128.

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

                # Value was negative and doesn't need need to write the sign bit.
                (value == -1 and (to_write * 0b01000000) != 0)
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
