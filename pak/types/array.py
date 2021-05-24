""":class:`Types <.Type>` for contiguous data."""

import inspect

from .. import util
from .type import Type
from .misc import RawByte, Padding

__all__ = [
    "Array",
]

class Array(Type):
    """A :class:`~.Type` for contiguous data.

    Parameters
    ----------
    elem_type : typelike
        The :class:`~.Type` contained in the :class:`Array`.
    size : :class:`int` or typelike or :class:`str` or :class:`function` or ``None``
        The size of the :class:`Array`.

        If an :class:`int`, then the :class:`Array` has a fixed size
        of ``size``.

        If a typelike, then the :class:`Array` is prefixed by ``size``,
        and its value determines the amount of values in the array.

        If a :class:`str`, then the size is determined by getting the
        attribute of the same name from the :class:`~.Packet` instance.
        Internally this is translated to a :class:`function` size.

        If a :class:`function`, then the size is determined by passing the
        packet instance into the :class`function`.

        If ``None``, then the :class:`Array` is read until the end of
        the buffer.
    """

    elem_type  = None
    array_size = None

    @classmethod
    def is_padding(cls):
        """Gets whether the :class:`Array` is for
        :class:`~.Padding`, which is special-cased
        for longer strings of padding.

        Returns
        -------
        :class:`bool`
            Whether the :class:`Array` is for :class:`~.Padding`.
        """

        return cls.elem_type is Padding

    @classmethod
    def is_raw_byte(cls):
        """Gets whether the :class:`Array` is for
        :class:`~.RawByte`, which is special-cased to
        have a :class:`bytearray` value.

        Returns
        -------
        :class:`bool`
            Whether the :class:`Array` is for :class:`~.RawByte`.
        """

        return cls.elem_type is RawByte

    @classmethod
    def is_fixed_size(cls):
        """Gets whether the :class:`Array` has a fixed size.

        Returns
        -------
        :class:`bool`
            Whether the :class:`Array` has a fixed size.
        """

        return isinstance(cls.array_size, int)

    @classmethod
    def is_prefixed_by_type(cls):
        """Gets whether the :class:`Array` is prefixed by a :class:`~.Type`.

        Returns
        -------
        :class:`bool`
            Whether the :class:`Array` is prefixed by a :class:`~.Type`.
        """

        return isinstance(cls.array_size, type) and issubclass(cls.array_size, Type)

    @classmethod
    def has_size_function(cls):
        """Gets whether the size of the :class:`Array` is determined by a function.

        Returns
        -------
        :class:`bool`
            Whether the size is determined by a function.
        """

        return inspect.isfunction(cls.array_size)

    @classmethod
    def should_read_until_end(cls):
        """Gets whether the :class:`Array` should read until the end of the buffer.

        Returns
        -------
        :class:`bool`
            Whether the :class:`Array` should read until the end of the buffer.
        """

        return cls.array_size is None

    @classmethod
    def real_size(cls, *, ctx=None):
        """Gets the real size of the :class:`Array` based on the :class:`~.TypeContext`.

        Parameters
        ----------
        ctx : :class:`~.TypeContext`
            The context for the :class:`~.Type`.

        Returns
        -------
        :class:`int`
            The real size of the :class:`Array`.
        """

        if cls.is_fixed_size():
            return cls.array_size

        if cls.is_prefixed_by_type():
            return cls.array_size.default(ctx=ctx)

        if cls.has_size_function():
            return cls.array_size(ctx.packet)

        return 0

    def __get__(self, instance, owner=None):
        if self.is_padding():
            return None

        return super().__get__(instance, owner)

    def __set__(self, instance, value):
        if self.is_padding():
            return

        if self.is_raw_byte():
            value = bytearray(value)

        super().__set__(instance, value)

    def __delete__(self, instance):
        if self.is_padding():
            return

        super().__delete__(instance)

    @classmethod
    def _size(cls, *, ctx=None):
        if cls.is_fixed_size():
            return cls.array_size * cls.elem_type.size()

        if cls.has_size_function():
            return cls.array_size(ctx.packet) * cls.elem_type.size()

        raise TypeError(f"{cls.__name__} has no set size")

    @classmethod
    def _default(cls, *, ctx=None):
        if cls.is_padding():
            return None

        if cls.is_raw_byte():
            return bytearray(cls.real_size(ctx=ctx))

        return [cls.elem_type.default(ctx=ctx) for x in range(cls.real_size(ctx=ctx))]

    @staticmethod
    def _read_data(buf, size, *, name="data"):
        data = buf.read(size)
        if len(data) < size:
            raise util.BufferOutOfDataError(f"Reading {name} failed")

        return data

    @classmethod
    def _unpack(cls, buf, *, ctx=None):
        if cls.should_read_until_end():
            if cls.is_padding():
                buf.read()
                return None

            if cls.is_raw_byte():
                return bytearray(buf.read())

            ret = []
            while True:
                try:
                    ret.append(cls.elem_type.unpack(buf, ctx=ctx))
                except:
                    return ret

        if cls.is_prefixed_by_type():
            size = cls.array_size.unpack(buf, ctx=ctx)

            if cls.is_padding():
                cls._read_data(buf, size, name="padding")

                return None

            if cls.is_raw_byte():
                return bytearray(cls._read_data(buf, size))

            return [cls.elem_type.unpack(buf, ctx=ctx) for x in range(size)]

        size = cls.real_size(ctx=ctx)

        if cls.is_padding():
            cls._read_data(buf, size, name="padding")

            return None

        if cls.is_raw_byte():
            return bytearray(cls._read_data(buf, size))

        return [cls.elem_type.unpack(buf, ctx=ctx) for x in range(size)]

    @classmethod
    def _pack(cls, value, *, ctx=None):
        if cls.should_read_until_end():
            if cls.is_padding():
                return b""

            if cls.is_raw_byte():
                return bytes(value)

            return b"".join(cls.elem_type.pack(x, ctx=ctx) for x in value)

        if cls.is_prefixed_by_type():
            if cls.is_padding():
                return cls.array_size.pack(0, ctx=ctx)

            prefix = cls.array_size.pack(len(value), ctx=ctx)

            if cls.is_raw_byte():
                return prefix + bytes(value)

            return prefix + b"".join(cls.elem_type.pack(x, ctx=ctx) for x in value)

        size = cls.real_size(ctx=ctx)

        if cls.is_padding():
            return b"\x00" * size

        if cls.is_raw_byte():
            return bytes(value[:size]) + bytes(max(0, size - len(value)))

        value = value[:size] + [cls.elem_type.default(ctx=ctx) for x in range(size - len(value))]

        return b"".join(cls.elem_type.pack(x, ctx=ctx) for x in value)

    @classmethod
    @Type.prepare_types
    def _call(cls, elem_type: Type, size=None):
        if isinstance(size, type):
            size_name = size.__name__
        else:
            size_name = repr(size)

        if isinstance(size, str):
            attr = size
            size = lambda x: getattr(x, attr)

        return cls.make_type(
            f"{elem_type.__name__}[{size_name}]",

            elem_type  = elem_type,
            array_size = size,
        )
