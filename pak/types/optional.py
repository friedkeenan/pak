r""":class:`~.Type`\s for marshaling data that might exist."""

import inspect

from .type import Type

__all__ = [
    "Optional",
]

class Optional(Type):
    """A :class:`~.Type` that might exist.

    Parameters
    ----------
    elem_type : typelike
        The underlying :class:`~.Type`.
    exists : subclass of :class:`~.Type` or :class:`str` or :class:`function` or ``None``
        If a subclass of :class:`~.Type`, then ``exists``
        should be a boolean :class:`~.Type`, such as
        :class:`~.Bool`, that says whether ``elem_type``
        exists or not.

        .. note::

            This argument doesn't accept all typelikes.
            If you need to pass a typelike that's not a
            subclass of :class:`~.Type`, then convert it
            first.

        If a :class:`str`, then whether ``elem_type`` exists
        is determined by getting that attribute of the
        same name from the :class:`~.Packet` instance.
        Internally this is translated to a :class:`function`.

        If a :class:`function`, then whether ``elem_type``
        exists is determined by passing the :class:`~.Packet`
        instance to the :class:`function`.

        If ``None`` then ``elem_type`` is assumed to be at the
        end of the raw data, and is attempted to be read. If
        it can't, then it is assumed that it doesn't exist.
    """

    elem_type = None
    exists    = None

    @classmethod
    def is_prefixed_by_type(cls):
        """Gets whether the :class:`Optional` is prefixed by a :class:`~.Type`.

        Returns
        -------
        :class:`bool`
            Whether the :class:`Optional` is prefixed by a :class:`~.Type`.
        """

        return isinstance(cls.exists, type) and issubclass(cls.exists, Type)

    @classmethod
    def has_function(cls):
        """Gets whether the existence of the underlying :class:`~.Type`
        is determined by a :class:`function`.

        Returns
        -------
        :class:`bool`
            Whether the existence of the underlying
            :class:`~.Type` is determined by a :class:`function`.
        """

        return inspect.isfunction(cls.exists)

    @classmethod
    def is_at_end(cls):
        """Gets whether the :class:`Optional` is at the end of the raw data.

        Returns
        -------
        :class:`bool`
            Whether the :class:`Optional` is at the end of the raw data.

            .. note::
                This is only an assumption and the
                :class:`Optional` does not *need* to
                be at the end of the raw data.
        """

        return cls.exists is None

    @classmethod
    def _default(cls, *, ctx):
        if cls.has_function() and cls.exists(ctx.packet):
            return cls.elem_type.default(ctx=ctx)

        return None

    @classmethod
    def _unpack(cls, buf, *, ctx):
        if cls.is_prefixed_by_type():
            exists = cls.exists.unpack(buf, ctx=ctx)
            if exists:
                return cls.elem_type.unpack(buf, ctx=ctx)
        elif cls.has_function():
            if cls.exists(ctx.packet):
                return cls.elem_type.unpack(buf, ctx=ctx)
        elif cls.is_at_end():
            try:
                return cls.elem_type.unpack(buf, ctx=ctx)
            except Exception:
                return None

        return None

    @classmethod
    def _pack(cls, value, *, ctx):
        if cls.is_prefixed_by_type():
            if value is not None:
                prefix = cls.exists.pack(True, ctx=ctx)

                return prefix + cls.elem_type.pack(value, ctx=ctx)

            return cls.exists.pack(False, ctx=ctx)

        if cls.has_function():
            if cls.exists(ctx.packet):
                return cls.elem_type.pack(value, ctx=ctx)

            return b""

        if cls.is_at_end():
            if value is not None:
                return cls.elem_type.pack(value, ctx=ctx)

            return b""

        return b""

    @classmethod
    @Type.prepare_types
    def _call(cls, elem_type: Type, exists=None):
        if isinstance(exists, str):
            attr   = exists
            exists = lambda x: getattr(x, attr)

        return cls.make_type(
            f"{cls.__qualname__}{elem_type.__qualname__}",

            elem_type = elem_type,
            exists    = exists,
        )
