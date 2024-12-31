r""":class:`.Type`\s which defer their behavior to other :class:`.Type`\s."""

from .type import Type

__all__ = [
    "DeferringType",
]

class DeferringType(Type):
    r"""A :class:`.Type` which defers its behavior to other :class:`.Type`\s.

    A :class:`DeferringType` will defer all of its marshaling behavior
    to a certain :class:`.Type` depending on what it decides to return
    from its :meth:`_defer_to` method.

    This deferring of behavior is useful, for instance, in
    protocols with multiple versions, where you may want
    to have a :class:`.Packet` field act like a different
    :class:`.Type` between different protocol versions.

    :class:`DeferringType` should be preferred to custom :class:`.Type`\s
    of a similar nature because :class:`DeferringType` will forward on
    all relevant behavior, resulting in a more correct and ergonomic experience.

    Examples
    --------
    >>> import pak
    >>> class VersionedPacket(pak.Packet):
    ...     class Context(pak.Packet.Context):
    ...         def __init__(self, *, version):
    ...             self.version = version
    ...
    ...             super().__init__()
    ...
    ...         def __hash__(self):
    ...             return hash(self.version)
    ...
    ...         def __eq__(self, other):
    ...             if not isinstance(other, VersionedPacket.Context):
    ...                 return NotImplemented
    ...
    ...             return self.version == other.version
    ...
    >>> class VersionedInteger(pak.DeferringType):
    ...     @classmethod
    ...     def _defer_to(cls, *, ctx):
    ...         # 'Int8' in version 0, 'Int16' in every other version.
    ...         if ctx.version == 0:
    ...             return pak.Int8
    ...
    ...         return pak.Int16
    ...
    >>> class MyPacket(VersionedPacket):
    ...     number: VersionedInteger
    ...
    >>> p = MyPacket(number=2)
    >>>
    >>> # The 'number' field is an 'Int8' in version 0.
    >>> p.pack(ctx=VersionedPacket.Context(version=0))
    b'\x02'
    >>>
    >>> # The 'number' field is an 'Int16' in version 1.
    >>> p.pack(ctx=VersionedPacket.Context(version=1))
    b'\x02\x00'
    """

    class UnableToDeferError(ValueError, Type.UnsuppressedError):
        """An error indicating that there was no appropriate :class:`.Type` to defer to."""

    @classmethod
    def _defer_to(cls, *, ctx):
        """Gets the :class:`.Type` which the :class:`DeferringType` should defer to.

        This method should be overridden by subclasses.

        Parameters
        ----------
        ctx : :class:`.Type.Context`
            The context for the :class:`.Type`.

        Returns
        -------
        subclass of :class:`.Type`
            The appropriate :class:`.Type` to defer to
            based on the ``ctx`` parameter.

        Raises
        ------
        :exc:`UnableToDeferError`
            If the :class:`DeferringType` is unable
            to defer to an appropriate :class:`.Type`.
        """

        raise cls.UnableToDeferError(f"'{cls.__qualname__}' has not implemented deferring")

    # NOTE: We cannot defer in our descriptor special methods
    # as there is no context available there for us to inspect.

    @classmethod
    def _size(cls, value, *, ctx):
        return cls._defer_to(ctx=ctx).size(value, ctx=ctx)

    @classmethod
    def _alignment(cls, *, ctx):
        return cls._defer_to(ctx=ctx).alignment(ctx=ctx)

    @classmethod
    def _default(cls, *, ctx):
        return cls._defer_to(ctx=ctx).default(ctx=ctx)

    @classmethod
    def _unpack(cls, buf, *, ctx):
        return cls._defer_to(ctx=ctx).unpack(buf, ctx=ctx)

    @classmethod
    async def _unpack_async(cls, reader, *, ctx):
        return await cls._defer_to(ctx=ctx).unpack_async(reader, ctx=ctx)

    @classmethod
    def _pack(cls, value, *, ctx):
        return cls._defer_to(ctx=ctx).pack(value, ctx=ctx)

    @classmethod
    def _array_static_size(cls, array_size, *, ctx):
        return cls._defer_to(ctx=ctx)._array_static_size(array_size, ctx=ctx)

    @classmethod
    def _array_default(cls, array_size, *, ctx):
        return cls._defer_to(ctx=ctx)._array_default(array_size, ctx=ctx)

    @classmethod
    def _array_unpack(cls, buf, array_size, *, ctx):
        return cls._defer_to(ctx=ctx)._array_unpack(buf, array_size, ctx=ctx)

    @classmethod
    async def _array_unpack_async(cls, reader, array_size, *, ctx):
        return await cls._defer_to(ctx=ctx)._array_unpack_async(reader, array_size, ctx=ctx)

    @classmethod
    def _array_num_elements(cls, value, *, ctx):
        return cls._defer_to(ctx=ctx)._array_num_elements(value, ctx=ctx)

    @classmethod
    def _array_ensure_size(cls, value, array_size, *, ctx):
        return cls._defer_to(ctx=ctx)._array_ensure_size(value, array_size, ctx=ctx)

    @classmethod
    def _array_pack(cls, value, array_size, *, ctx):
        return cls._defer_to(ctx=ctx)._array_pack(value, array_size, ctx=ctx)
