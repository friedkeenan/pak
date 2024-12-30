r""":class:`.Type`\s for numbers."""

from .. import util
from .type import Type, MaxBytesExceededError
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

# NOTE: I'm not utterly content with the
# amount of code duplication involved with
# the 'LEB128' types, but I think it's
# ultimately fine even if annoying.

class LEB128(Type):
    """A variable length signed integer following the ``LEB128`` format."""

    _default = 0

    class Limited(Type):
        """An :class:`LEB128` which is limited to a certain number of bytes.

        It may be useful to limit the number of bytes
        which may be marshaled in order to prevent a
        malicious actor from endlessly setting the top
        bit of each byte so that unpacking never ends.

        By limiting the number of bytes, then
        unpacking is always guaranteed to end.

        When unpacking, if the number of bytes exceeds the
        specified maximum, then a :exc:`.MaxBytesExceededError`
        will be raised.

        When packing, if the to-be-packed value exceeds the
        associated range of values for the maximum number of
        bytes, then a :exc:`ValueError` will be raised.

        Parameters
        ----------
        max_bytes : :class:`int`
            The number of bytes to limit the :class:`LEB128` to.
        """

        _default = 0

        max_bytes = None

        @classmethod
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)

            if cls.max_bytes is not None:
                max_bits = cls.max_bytes * 7

                cls._value_range = range(-util.bit(max_bits - 1), util.bit(max_bits - 1))

        @classmethod
        def _unpack(cls, buf, *, ctx):
            num = 0

            for i in range(cls.max_bytes):
                byte = UInt8.unpack(buf, ctx=ctx)

                # Get the bottom 7 bits.
                value = byte & 0b01111111

                num |= value << (i * 7)

                # If the top bit is not set, return.
                if byte & 0b10000000 == 0:
                    return util.to_signed(num, bits=(i + 1) * 7)

            raise MaxBytesExceededError(cls)

        @classmethod
        async def _unpack_async(cls, reader, *, ctx):
            num = 0

            for i in range(cls.max_bytes):
                byte = await UInt8.unpack_async(reader, ctx=ctx)

                # Get the bottom 7 bits.
                value = byte & 0b01111111

                num |= value << (i * 7)

                # If the top bit is not set, return.
                if byte & 0b10000000 == 0:
                    return util.to_signed(num, bits=(i + 1) * 7)

            raise MaxBytesExceededError(cls)

        @classmethod
        def _pack(cls, value, *, ctx):
            # If 'value' is not an 'int' then checking if
            # it's contained in the value range will loop
            # through the quite large range instead of just
            # comparing against the start and end.
            #
            # Therefore we decide to just not worry about
            # non-integer values.
            if isinstance(value, int) and value not in cls._value_range:
                raise ValueError(f"Value '{value}' is out of the range of '{cls.__qualname__}'")

            return LEB128.pack(value, ctx=ctx)

        @classmethod
        def _call(cls, *, max_bytes):
            return cls.make_type(
                f"{cls.__qualname__}(max_bytes={max_bytes})",

                max_bytes = max_bytes,
            )

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
    async def _unpack_async(cls, reader, *, ctx):
        num = 0

        bits = 0
        while True:
            byte = await UInt8.unpack_async(reader, ctx=ctx)

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

    class Limited(Type):
        """An :class:`ULEB128` which is limited to a certain number of bytes.

        It may be useful to limit the number of bytes
        which may be marshaled in order to prevent a
        malicious actor from endlessly setting the top
        bit of each byte so that unpacking never ends.

        By limiting the number of bytes, then
        unpacking is always guaranteed to end.

        When unpacking, if the number of bytes exceeds the
        specified maximum, then a :exc:`.MaxBytesExceededError`
        will be raised.

        When packing, if the to-be-packed value exceeds the
        associated range of values for the maximum number of
        bytes, then a :exc:`ValueError` will be raised.

        Parameters
        ----------
        max_bytes : :class:`int`
            The number of bytes to limit the :class:`ULEB128` to.
        """

        _default = 0

        max_bytes = None

        @classmethod
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)

            if cls.max_bytes is not None:
                max_bits = cls.max_bytes * 7

                cls._value_range = range(util.bit(max_bits))

        @classmethod
        def _unpack(cls, buf, *, ctx):
            num = 0

            for i in range(cls.max_bytes):
                byte = UInt8.unpack(buf, ctx=ctx)

                # Get the bottom 7 bits.
                value = byte & 0b01111111

                num |= value << (i * 7)

                # If the top bit is not set, return.
                if byte & 0b10000000 == 0:
                    return num

            raise MaxBytesExceededError(cls)

        @classmethod
        async def _unpack_async(cls, reader, *, ctx):
            num = 0

            for i in range(cls.max_bytes):
                byte = await UInt8.unpack_async(reader, ctx=ctx)

                # Get the bottom 7 bits.
                value = byte & 0b01111111

                num |= value << (i * 7)

                # If the top bit is not set, return.
                if byte & 0b10000000 == 0:
                    return num

            raise MaxBytesExceededError(cls)

        @classmethod
        def _pack(cls, value, *, ctx):
            # If 'value' is not an 'int' then checking if
            # it's contained in the value range will loop
            # through the quite large range instead of just
            # comparing against the start and end.
            #
            # Therefore we decide to just not worry about
            # non-integer values.
            if isinstance(value, int) and value not in cls._value_range:
                raise ValueError(f"Value '{value}' is out of the range of '{cls.__qualname__}'")

            return ULEB128.pack(value, ctx=ctx)

        @classmethod
        def _call(cls, *, max_bytes):
            return cls.make_type(
                f"{cls.__qualname__}(max_bytes={max_bytes})",

                max_bytes = max_bytes,
            )

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
    async def _unpack_async(cls, reader, *, ctx):
        num = 0

        bits = 0
        while True:
            byte = await UInt8.unpack_async(reader, ctx=ctx)

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
    async def _unpack_async(cls, reader, *, ctx):
        return await cls.elem_type.unpack_async(reader, ctx=ctx) / cls.divisor

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
