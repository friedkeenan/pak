"""Miscellaneous types."""

import struct

from .. import util
from .type import Type

__all__ = [
    "EmptyType",
    "RawByte",
    "Padding",
    "StructType",
]

class EmptyType(Type):
    """A :class:`~.Type` of no value.

    It always unpacks to ``None`` and always packs
    to ``b""``. It is useful in certain cases when you
    would want to "disable" a packet field for instance.

    ``None`` is a typelike value that translates to
    :class:`EmptyType`.
    """

    _size = 0

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

        return None

    def __set__(self, instance, value):
        pass

    def __delete__(self, instance):
        pass

    @classmethod
    def _default(cls, *, ctx=None):
        return None

    @classmethod
    def _unpack(cls, buf, *, ctx=None):
        return None

    @classmethod
    def _pack(cls, value, *, ctx=None):
        return b""

Type.register_typelike(type(None), lambda x: EmptyType)

class Padding(Type):
    """A single byte of padding.

    This :class:`~.Type` will marshal one byte to
    ``None``, and any value to ``b"\\x00"``.

    It is also special-cased in :class:`~.Array`
    for padding of larger length.
    """

    _size = 1

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

        return None

    def __set__(self, instance, value):
        pass

    def __delete__(self, instance):
        pass

    @classmethod
    def _default(cls, *, ctx=None):
        return None

    @classmethod
    def _unpack(cls, buf, *, ctx=None):
        if len(buf.read(1)) < 1:
            raise util.BufferOutOfDataError("Reading padding failed")

        return None

    @classmethod
    def _pack(cls, value, *, ctx=None):
        return b"\x00"

class RawByte(Type):
    """A single byte of data.

    The main reason this exists is to be used
    along with :class:`~.Array`, for which this
    :class:`~.Type` is special-cased to produce a
    :class:`bytearray` value.
    """

    _size    = 1
    _default = b"\x00"

    @classmethod
    def _unpack(cls, buf, *, ctx=None):
        byte = buf.read(1)

        if len(byte) < 1:
            raise util.BufferOutOfDataError("Reading byte failed")

        return byte

    @classmethod
    def _pack(cls, value, *, ctx=None):
        return bytes(value[:1])

class StructType(Type):
    """A wrapper over :func:`struct.pack` and :func:`struct.unpack`.

    :meta no-undoc-members:

    Attributes
    ----------
    fmt : :class:`str`
        The format string for the structure, not including
        the endianness prefix.
    endian : :class:`str`
        The endianness prefix used in :mod:`struct`.

        By default little endian.
    """

    fmt    = None
    endian = "<"

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # Compile a struct.Struct on class initialization
        cls.struct = struct.Struct(f"{cls.endian}{cls.fmt}")

    @classmethod
    def _size(cls, *, ctx=None):
        return cls.struct.size

    @classmethod
    def _unpack(cls, buf, *, ctx=None):
        ret = cls.struct.unpack(buf.read(cls.struct.size))

        if len(ret) == 1:
            return ret[0]

        return ret

    @classmethod
    def _pack(cls, value, *, ctx=None):
        if util.is_iterable(value):
            return cls.struct.pack(*value)

        return cls.struct.pack(value)
