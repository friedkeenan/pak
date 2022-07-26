r""":class:`~.Type`\s for contiguous data of the same :class:`~.Type`."""

import collections
import inspect

from .type import Type

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
        :class:`~.Packet` instance to the :class:`function`.

        If ``None``, then the :class:`Array` is read until the end of
        the buffer.
    """

    elem_type  = None
    array_size = None

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
        """Gets whether the size of the :class:`Array`
        is determined by a :class:`function`.

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
    def default_size(cls, *, ctx):
        """Gets the default size of the :class:`Array` based on the :class:`.Type.Context`.

        Parameters
        ----------
        ctx : :class:`.Type.Context`
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

    def __set__(self, instance, value):
        value = self.elem_type._array_transform_value(value)

        super().__set__(instance, value)

    @classmethod
    def _size(cls, value, *, ctx):
        if cls.is_fixed_size():
            array_size = cls.array_size
        elif cls.has_size_function():
            array_size = cls.array_size(ctx.packet)
        else:
            if value is cls.STATIC_SIZE:
                return None

            array_size = cls.elem_type._array_num_elements(value, ctx=ctx)

        # If we can't get a static size of the element type, then
        # don't bother with any calculations.
        body_size = cls.elem_type._array_static_size(array_size, ctx=ctx)
        if body_size is None:
            return None

        if cls.is_prefixed_by_type():
            return cls.array_size.size(array_size, ctx=ctx) + body_size

        return body_size

    @classmethod
    def _alignment(cls, *, ctx):
        if cls.is_prefixed_by_type() or cls.should_read_until_end():
            return None

        return cls.elem_type.alignment(ctx=ctx)

    @classmethod
    def _default(cls, *, ctx):
        return cls.elem_type._array_default(cls.default_size(ctx=ctx), ctx=ctx)

    @classmethod
    def _unpack(cls, buf, *, ctx):
        if cls.should_read_until_end():
            size = None
        elif cls.is_prefixed_by_type():
            size = cls.array_size.unpack(buf, ctx=ctx)
        else:
            size = cls.default_size(ctx=ctx)

        return cls.elem_type._array_unpack(buf, size, ctx=ctx)

    @classmethod
    def _pack(cls, value, *, ctx):
        if cls.is_prefixed_by_type() or cls.should_read_until_end():
            size = cls.elem_type._array_num_elements(value, ctx=ctx)
        else:
            size  = cls.default_size(ctx=ctx)
            value = cls.elem_type._array_ensure_size(value, size, ctx=ctx)

        data = cls.elem_type._array_pack(value, size, ctx=ctx)

        if cls.is_prefixed_by_type():
            data = cls.array_size.pack(size, ctx=ctx) + data

        return data

    @classmethod
    @Type.prepare_types
    def _call(cls, elem_type: Type, size=None):
        if isinstance(size, type):
            size_name = size.__qualname__
        else:
            size_name = repr(size)

        if isinstance(size, str):
            attr = size
            size = lambda x: getattr(x, attr)

        return cls.make_type(
            f"{elem_type.__qualname__}[{size_name}]",

            elem_type  = elem_type,
            array_size = size,
        )
