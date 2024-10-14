r""":class:`.Type`\s for contiguous data of the same :class:`.Type`."""

from .type import Type

__all__ = [
    "Array",
]

class Array(Type):
    """A :class:`.Type` for contiguous data.

    Parameters
    ----------
    elem_type : typelike
        The :class:`.Type` contained in the :class:`Array`.
    size : :class:`int` or typelike or :class:`str` or :class:`function` or ``None``
        The size of the :class:`Array`.

        If an :class:`int`, then the :class:`Array` has a fixed size
        of ``size``. This case will be deferred to :class:`Array.FixedSize`.

        If a typelike, then the :class:`Array` is prefixed by the typelike,
        and its value determines the number of elements in the :class:`Array`.
        This case will be deferred to :class:`Array.SizePrefixed`.

        If ``None``, then the :class:`Array` is read until the end of
        the buffer. This case will be deferred to :class:`Array.Unbounded`.

        If a :class:`str`, then the size is determined by getting the
        attribute of the same name from the :class:`.Packet` instance.
        This case will be deferred to :class:`Array.FunctionSized`.

        If a :class:`function`, then the size is determined by passing the
        :class:`.Packet` instance to the :class:`function`. This case will
        be deferred to :class:`Array.FunctionSized`.
    """

    elem_type  = None
    array_size = None

    # The following classes will be
    # replaced after 'Array' is defined.
    #
    # These dummy classes are defined here
    # to have the docs properly ordered.
    #
    # These classes need to be defined after
    # 'Array' because they inherit from it.

    class FixedSize:
        pass

    class SizePrefixed:
        pass

    class Unbounded:
        pass

    class FunctionSized:
        pass

    def __set__(self, instance, value):
        value = self.elem_type._array_transform_value(value)

        super().__set__(instance, value)

    @classmethod
    @Type.prepare_types
    def _call(cls, elem_type: Type, size=None):
        if size is None:
            return cls.Unbounded(elem_type)

        if isinstance(size, int):
            return cls.FixedSize(elem_type, size)

        if Type.is_typelike(size):
            return cls.SizePrefixed(elem_type, size)

        return cls.FunctionSized(elem_type, size)

class _FixedSize(Array):
    r"""An :class:`Array` with a fixed size.

    Parameters
    ----------
    elem_type : typelike
        The :class:`.Type` contained in the :class:`Array`.
    size : :class:`int`
        The number of elements in the :class:`Array`.

    Examples
    --------
    >>> import pak
    >>> pak.Int8[2].unpack(b"\x00\x01")
    [0, 1]
    >>> pak.Int8[2].pack([0, 1])
    b'\x00\x01'
    """

    @classmethod
    def _size(cls, value, *, ctx):
        return cls.elem_type._array_static_size(cls.array_size, ctx=ctx)

    @classmethod
    def _alignment(cls, *, ctx):
        return cls.elem_type.alignment(ctx=ctx)

    @classmethod
    def _default(cls, *, ctx):
        return cls.elem_type._array_default(cls.array_size, ctx=ctx)

    @classmethod
    def _unpack(cls, buf, *, ctx):
        return cls.elem_type._array_unpack(buf, cls.array_size, ctx=ctx)

    @classmethod
    async def _unpack_async(cls, reader, *, ctx):
        return await cls.elem_type._array_unpack_async(reader, cls.array_size, ctx=ctx)

    @classmethod
    def _pack(cls, value, *, ctx):
        value = cls.elem_type._array_ensure_size(value, cls.array_size, ctx=ctx)

        return cls.elem_type._array_pack(value, cls.array_size, ctx=ctx)

    @classmethod
    @Type.prepare_types
    def _call(cls, elem_type: Type, size):
        return cls.make_type(
            f"{elem_type.__qualname__}[{size}]",

            elem_type  = elem_type,
            array_size = size,
        )

class _SizePrefixed(Array):
    r"""An :class:`Array` which is prefixed by the number of its elements.

    Parameters
    ----------
    elem_type : typelike
        The :class:`.Type` contained in the :class:`Array`.
    size : typelike
        The :class:`.Type` which corresponds to the prefixed size value.

    Examples
    --------
    >>> import pak
    >>> pak.Int8[pak.Int8].unpack(b"\x02\x00\x01")
    [0, 1]
    >>> pak.Int8[pak.Int8].pack([0, 1])
    b'\x02\x00\x01'
    """

    @classmethod
    def _size(cls, value, *, ctx):
        if value is cls.STATIC_SIZE:
            return None

        array_size = cls.elem_type._array_num_elements(value, ctx=ctx)

        body_size = cls.elem_type._array_static_size(array_size, ctx=ctx)
        if body_size is None:
            return None

        return cls.array_size.size(array_size, ctx=ctx) + body_size

    @classmethod
    def _default(cls, *, ctx):
        return cls.elem_type._array_default(cls.array_size.default(ctx=ctx), ctx=ctx)

    @classmethod
    def _unpack(cls, buf, *, ctx):
        size = cls.array_size.unpack(buf, ctx=ctx)

        return cls.elem_type._array_unpack(buf, size, ctx=ctx)

    @classmethod
    async def _unpack_async(cls, reader, *, ctx):
        size = await cls.array_size.unpack_async(reader, ctx=ctx)

        return await cls.elem_type._array_unpack_async(reader, size, ctx=ctx)

    @classmethod
    def _pack(cls, value, *, ctx):
        size = cls.elem_type._array_num_elements(value, ctx=ctx)

        return (
            cls.array_size.pack(size, ctx=ctx) +

            cls.elem_type._array_pack(value, size, ctx=ctx)
        )

    @classmethod
    @Type.prepare_types
    def _call(cls, elem_type: Type, size: Type):
        return cls.make_type(
            f"{elem_type.__qualname__}[{size.__qualname__}]",

            elem_type  = elem_type,
            array_size = size,
        )

class _Unbounded(Array):
    r"""An unbounded :class:`Array`.

    An unbounded :class:`Array` will read its elements until the end of the buffer.

    Parameters
    ----------
    elem_type : typelike
        The :class:`.Type` contained in the :class:`Array`.

    Examples
    --------
    >>> import pak
    >>> pak.Int8[None].unpack(b"\x00\x01\x02")
    [0, 1, 2]
    >>> pak.Int8[None].pack([0, 1, 2])
    b'\x00\x01\x02'
    """

    @classmethod
    def _size(cls, value, *, ctx):
        if value is cls.STATIC_SIZE:
            return None

        array_size = cls.elem_type._array_num_elements(value, ctx=ctx)

        return cls.elem_type._array_static_size(array_size, ctx=ctx)

    @classmethod
    def _default(cls, *, ctx):
        return cls.elem_type._array_default(0, ctx=ctx)

    @classmethod
    def _unpack(cls, buf, *, ctx):
        return cls.elem_type._array_unpack(buf, None, ctx=ctx)

    @classmethod
    async def _unpack_async(cls, reader, *, ctx):
        return await cls.elem_type._array_unpack_async(reader, None, ctx=ctx)

    @classmethod
    def _pack(cls, value, *, ctx):
        size = cls.elem_type._array_num_elements(value, ctx=ctx)

        return cls.elem_type._array_pack(value, size, ctx=ctx)

    @classmethod
    @Type.prepare_types
    def _call(cls, elem_type: Type):
        return cls.make_type(
            f"{elem_type.__qualname__}[None]",

            elem_type  = elem_type,
            array_size = None,
        )

class _FunctionSized(Array):
    r"""An :class:`Array` whose size is determined by calling a :class:`function`.

    The :class:`function` will be passed the relevant :class:`.Packet` instance,
    and should return the number of elements in the :class:`Array`.

    Parameters
    ----------
    elem_type : typelike
        The :class:`.Type` contained in the :class:`Array`.
    size : :class:`function` or :class:`str`
        If a :class:`function`, then the number of elements of
        the :class:`Array` is determined by calling the :class:`function`
        with the relevant :class:`.Packet` instance.

        If a :class:`str`, then a :class:`function` which gets
        and returns the attribute named by the :class:`str` is
        used as the effective :class:`function` for the size
        of the :class:`Array`.

    Examples
    --------
    If a :class:`str` is used as ``size``::

        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     length: pak.Int8
        ...     array:  pak.Int8["length"]
        ...
        >>> packet = MyPacket.unpack(b"\x02\x00\x01")
        >>> packet
        MyPacket(length=2, array=[0, 1])
        >>> packet.pack()
        b'\x02\x00\x01'

    If a normal :class:`function` is used as ``size``::

        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     half_length: pak.Int8
        ...     array:       pak.Int8[lambda p: 2 * p.half_length]
        ...
        >>> packet = MyPacket.unpack(b'\x01\x00\x01')
        >>> packet
        MyPacket(half_length=1, array=[0, 1])
        >>> packet.pack()
        b'\x01\x00\x01'
    """

    @classmethod
    def _size(cls, value, *, ctx):
        # It does not make sense for a function-sized
        # array to have a static size because it would
        # depend on a non-static value (the relevant packet).
        if value is cls.STATIC_SIZE:
            return None

        array_size = cls.array_size(ctx.packet)

        return cls.elem_type._array_static_size(array_size, ctx=ctx)

    @classmethod
    def _default(cls, *, ctx):
        return cls.elem_type._array_default(cls.array_size(ctx.packet), ctx=ctx)

    @classmethod
    def _unpack(cls, buf, *, ctx):
        return cls.elem_type._array_unpack(buf, cls.array_size(ctx.packet), ctx=ctx)

    @classmethod
    async def _unpack_async(cls, reader, *, ctx):
        return await cls.elem_type._array_unpack_async(reader, cls.array_size(ctx.packet), ctx=ctx)

    @classmethod
    def _pack(cls, value, *, ctx):
        size  = cls.array_size(ctx.packet)
        value = cls.elem_type._array_ensure_size(value, size, ctx=ctx)

        return cls.elem_type._array_pack(value, size, ctx=ctx)

    @classmethod
    @Type.prepare_types
    def _call(cls, elem_type: Type, size):
        size_name = repr(size)

        if isinstance(size, str):
            attr = size
            size = lambda packet: getattr(packet, attr)

        return cls.make_type(
            f"{elem_type.__qualname__}[{size_name}]",

            elem_type  = elem_type,
            array_size = size,
        )

# Set the appropriate naming for the 'Array' specializations.

_FixedSize.__name__     = "FixedSize"
_FixedSize.__qualname__ = "Array.FixedSize"
Array.FixedSize         = _FixedSize

_SizePrefixed.__name__     = "SizePrefixed"
_SizePrefixed.__qualname__ = "Array.SizePrefixed"
Array.SizePrefixed         = _SizePrefixed

_Unbounded.__name__     = "Unbounded"
_Unbounded.__qualname__ = "Array.Unbounded"
Array.Unbounded         = _Unbounded

_FunctionSized.__name__     = "FunctionSized"
_FunctionSized.__qualname__ = "Array.FunctionSized"
Array.FunctionSized         = _FunctionSized

# Remove access to the specializations from
# their underline-prefixed names to stop
# them from showing up in the docs.

del _FixedSize
del _SizePrefixed
del _Unbounded
del _FunctionSized
