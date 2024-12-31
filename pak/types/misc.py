r"""Miscellaneous :class:`.Type`\s."""

import struct

from .. import util
from .type import Type

__all__ = [
    "EmptyType",
    "Padding",
    "RawByte",
    "StructType",
]

class EmptyType(Type):
    """A :class:`.Type` of no value.

    It always unpacks to ``None`` and always packs
    to ``b""``. It is useful in certain cases when you
    would want to "disable" a packet field for instance.

    ``None`` is a typelike value that translates to
    :class:`EmptyType`.
    """

    _size      = 0
    _alignment = 1

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

        return None

    def __set__(self, instance, value):
        pass

    def __delete__(self, instance):
        pass

    @classmethod
    def _default(cls, *, ctx):
        return None

    @classmethod
    def _unpack(cls, buf, *, ctx):
        return None

    @classmethod
    async def _unpack_async(cls, reader, *, ctx):
        return None

    @classmethod
    def _pack(cls, value, *, ctx):
        return b""

Type.register_typelike(type(None), lambda x: EmptyType)

class Padding(Type):
    r"""A single byte of padding.

    This :class:`.Type` will marshal one byte to
    ``None``, and any value to ``b"\x00"``.

    It is also special-cased in :class:`.Array`
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
    def _default(cls, *, ctx):
        return None

    @classmethod
    def _unpack(cls, buf, *, ctx):
        if len(buf.read(1)) < 1:
            raise util.BufferOutOfDataError("Reading padding failed")

        return None

    @classmethod
    async def _unpack_async(cls, reader, *, ctx):
        await reader.readexactly(1)

        return None

    @classmethod
    def _pack(cls, value, *, ctx):
        return b"\x00"

    @classmethod
    def _array_default(cls, array_size, *, ctx):
        return None

    @classmethod
    def _array_unpack(cls, buf, array_size, *, ctx):
        if array_size is None:
            buf.read()

            return None

        data = buf.read(array_size)
        if len(data) < array_size:
            raise util.BufferOutOfDataError("Reading padding failed")

        return None

    @classmethod
    async def _array_unpack_async(cls, reader, array_size, *, ctx):
        if array_size is None:
            await reader.read()

            return None

        await reader.readexactly(array_size)

        return None

    @classmethod
    def _array_num_elements(cls, value, *, ctx):
        return 0

    @classmethod
    def _array_ensure_size(cls, value, array_size, *, ctx):
        return None

    @classmethod
    def _array_pack(cls, value, array_size, *, ctx):
        return b"\00" * array_size

    @classmethod
    def _array_transform_value(cls, value):
        return None

class RawByte(Type):
    """A single byte of data.

    The main reason this exists is to be used
    along with :class:`.Array`, for which this
    :class:`.Type` is special-cased to produce a
    :class:`bytearray` value.
    """

    _size      = 1
    _alignment = 1
    _default   = b"\x00"

    @classmethod
    def _unpack(cls, buf, *, ctx):
        byte = buf.read(1)

        if len(byte) < 1:
            raise util.BufferOutOfDataError("Reading byte failed")

        return byte

    @classmethod
    async def _unpack_async(cls, reader, *, ctx):
        return await reader.readexactly(1)

    @classmethod
    def _pack(cls, value, *, ctx):
        return bytes(value[:1])

    @classmethod
    def _array_default(cls, array_size, *, ctx):
        return bytearray(array_size)

    @classmethod
    def _array_unpack(cls, buf, array_size, *, ctx):
        if array_size is None:
            return bytearray(buf.read())

        data = buf.read(array_size)
        if len(data) < array_size:
            raise util.BufferOutOfDataError("Reading data failed")

        return bytearray(data)

    @classmethod
    async def _array_unpack_async(cls, reader, array_size, *, ctx):
        if array_size is None:
            return bytearray(await reader.read())

        return bytearray(await reader.readexactly(array_size))

    @classmethod
    def _array_pack(cls, value, array_size, *, ctx):
        return bytes(value)

    @classmethod
    def _array_transform_value(cls, value):
        return bytearray(value)

class StructType(Type):
    """A wrapper over :func:`struct.pack` and :func:`struct.unpack`.

    Attributes
    ----------
    fmt : :class:`str`
        The format string for the structure,
        not including the endianness prefix.
    endian : :class:`str`
        The endianness prefix used in :mod:`struct`.

        By default little-endian.

        .. seealso::

            :meth:`little_endian`

            :meth:`big_endian`

            :meth:`native_endian`
    """

    #: :meta private:
    fmt = None

    #: :meta private:
    endian = "<"

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # Compile a struct.Struct on class initialization.
        if cls.fmt is not None:
            cls._struct = struct.Struct(f"{cls.endian}{cls.fmt}")
            cls._size   = cls._struct.size

    @classmethod
    def little_endian(cls):
        """Gets a little-endian version of the :class:`StructType`.

        Returns
        -------
        subclass of :class:`StructType`
            If the :class:`StructType` is already little-endian, then
            it is simply returned.

            Otherwise, a subclass with the proper endianness is returned.
        """

        if cls.endian == "<":
            return cls

        return cls.make_type(
            f"{cls.__qualname__}.little_endian()",

            endian = "<",
        )

    @classmethod
    def big_endian(cls):
        """Gets a big-endian version of the :class:`StructType`.

        Returns
        -------
        subclass of :class:`StructType`
            If the :class:`StructType` is already big-endian, then
            it is simply returned.

            Otherwise, a subclass with the proper endianness is returned.
        """

        if cls.endian == ">":
            return cls

        return cls.make_type(
            f"{cls.__qualname__}.big_endian()",

            endian = ">",
        )

    @classmethod
    def native_endian(cls):
        """Gets a native-endian version of the :class:`StructType`.

        Returns
        -------
        subclass of :class:`StructType`
            If the :class:`StructType` is already native-endian, then
            it is simply returned.

            Otherwise, a subclass with the proper endianness is returned.
        """

        if cls.endian == "=":
            return cls

        return cls.make_type(
            f"{cls.__qualname__}.native_endian()",

            endian = "=",
        )

    @classmethod
    def _unpack(cls, buf, *, ctx):
        ret = cls._struct.unpack(buf.read(cls._struct.size))

        if len(ret) == 1:
            return ret[0]

        return ret

    @classmethod
    async def _unpack_async(cls, reader, *, ctx):
        ret = cls._struct.unpack(await reader.readexactly(cls._struct.size))

        if len(ret) == 1:
            return ret[0]

        return ret

    @classmethod
    def _pack(cls, value, *, ctx):
        if util.is_iterable(value):
            return cls._struct.pack(*value)

        return cls._struct.pack(value)
