r""":class:`.Type`\s for marshaling data which might exist."""

from .type import Type

__all__ = [
    "Optional",
]

class Optional(Type):
    r"""A :class:`.Type` which might exist.

    Parameters
    ----------
    elem_type : typelike
        The underlying :class:`.Type`.
    exists : typelike or ``None`` or :class:`str` or :class:`function`
        If a typelike, then the :class:`Optional` is
        prefixed by the typelike and its value determines
        whether or not the :class:`Optional` exists.
        This case will be deferred to :class:`Optional.PrefixChecked`.

        If ``None``, then whether the :class:`Optional`
        exists is not checked, and is eagerly tried
        to be unpacked. This is usually used for
        :class:`Optional`\s at the end of the buffer.
        This case will be deferred to :class:`Optional.Unchecked`.

        If a :class:`str`, then whether the :class:`Optional`
        exists is determined by getting the attribute
        of the same name from the :class:`.Packet` instance.
        This case will be deferred to :class:`Optional.FunctionChecked`.

        If a :class:`function`, then whether the :class:`Optional`
        exists is determined by passing the :class:`.Packet`
        instance to the :class:`function`. This case will
        be deferred to :class:`Optional.FunctionChecked`.
    """

    elem_type = None
    exists    = None

    # The following classes will be
    # replaced after 'Optional' is defined.
    #
    # These dummy classes are defined here
    # to have the docs properly ordered.
    #
    # These classes need to be defined after
    # 'Optional' because they inherit from it.

    class PrefixChecked:
        pass

    class Unchecked:
        pass

    class FunctionChecked:
        pass

    @classmethod
    def _default(cls, *, ctx):
        return None

    @classmethod
    @Type.prepare_types
    def _call(cls, elem_type: Type, exists=None):
        if exists is None:
            return cls.Unchecked(elem_type)

        if Type.is_typelike(exists):
            return cls.PrefixChecked(elem_type, exists)

        return cls.FunctionChecked(elem_type, exists)

class _PrefixChecked(Optional):
    r"""An :class:`Optional` which exists if its prefix says so.

    Parameters
    ----------
    elem_type : typelike
        The underlying :class:`.Type`.
    exists : typelike
        A boolean :class:`.Type` which prefixes ``elem_type``,
        determining whether the :class:`Optional` exists or not.

    Examples
    --------
    >>> import pak
    >>> Prefixed = pak.Optional(pak.Int8, pak.Bool)
    >>> Prefixed.unpack(b"\x01\x02")
    2
    >>> Prefixed.pack(2)
    b'\x01\x02'
    >>>
    >>> assert Prefixed.unpack(b"\x00") is None
    >>> Prefixed.pack(None)
    b'\x00'
    """

    @classmethod
    def _size(cls, value, *, ctx):
        if value is cls.STATIC_SIZE:
            return None

        if value is None:
            return cls.exists.size(False, ctx=ctx)

        return cls.exists.size(True, ctx=ctx) + cls.elem_type.size(value, ctx=ctx)

    @classmethod
    def _unpack(cls, buf, *, ctx):
        if cls.exists.unpack(buf, ctx=ctx):
            return cls.elem_type.unpack(buf, ctx=ctx)

        return None

    @classmethod
    def _pack(cls, value, *, ctx):
        if value is None:
            return cls.exists.pack(False, ctx=ctx)

        return cls.exists.pack(True, ctx=ctx) + cls.elem_type.pack(value, ctx=ctx)

    @classmethod
    @Type.prepare_types
    def _call(cls, elem_type: Type, exists: Type):
        return cls.make_type(
            f"{cls.__qualname__}({elem_type.__qualname__}, {exists.__qualname__})",

            elem_type = elem_type,
            exists    = exists,
        )

class _Unchecked(Optional):
    r"""An :class:`Optional` which does not check whether it exists.

    Such :class:`Optional`\s are usually placed at the end of raw data.

    If any :exc:`Exception` is thrown while unpacking,
    then the :class:`Optional` does not exist.

    Parameters
    ----------
    elem_type : typelike
        The underlying :class:`.Type`.

    Examples
    --------
    >>> import pak
    >>> Unchecked = pak.Optional(pak.Int8)
    >>> Unchecked.unpack(b"\x01")
    1
    >>> Unchecked.pack(1)
    b'\x01'
    >>>
    >>> assert Unchecked.unpack(b"") is None
    >>> Unchecked.pack(None)
    b''
    """

    @classmethod
    def _size(cls, value, *, ctx):
        if value is cls.STATIC_SIZE:
            return None

        if value is None:
            return 0

        return cls.elem_type.size(value, ctx=ctx)

    @classmethod
    def _unpack(cls, buf, *, ctx):
        try:
            return cls.elem_type.unpack(buf, ctx=ctx)
        except Exception:
            return None

    @classmethod
    def _pack(cls, value, *, ctx):
        if value is None:
            return b""

        return cls.elem_type.pack(value, ctx=ctx)

    @classmethod
    @Type.prepare_types
    def _call(cls, elem_type: Type):
        return cls.make_type(
            f"{cls.__qualname__}({elem_type.__qualname__})",

            elem_type = elem_type,
            exists    = None,
        )

class _FunctionChecked(Optional):
    r"""An :class:`Optional` which exists if a :class:`function` says so.

    The :class:`function` will be passed the
    relevant :class:`.Packet` instance, and
    should return a :class:`bool` determining
    whether the :class:`Optional` exists.

    Parameters
    ----------
    elem_type : typelike
        The underlying :class:`.Type`.
    exists : :class:`function` or :class:`str`
        If a :class:`function`, then whether the
        :class:`Optional` exists is determined by
        calling the :class:`function` with the
        relevant :class:`.Packet` instance.

        If a :class:`str`, then a :class:`function`
        which gets and returns the attribute named
        by the :class:`str` is used as the effective
        :class:`function` for the existence of the
        :class:`Optional`.

    Examples
    --------
    If a :class:`str` is used as ``exists``::

        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     exists:   pak.Bool
        ...     optional: pak.Optional(pak.Int8, "exists")
        ...
        >>> packet = MyPacket.unpack(b"\x01\x02")
        >>> packet
        MyPacket(exists=True, optional=2)
        >>> packet.pack()
        b'\x01\x02'
        >>>
        >>> packet = MyPacket.unpack(b"\x00")
        >>> packet
        MyPacket(exists=False, optional=None)
        >>> packet.pack()
        b'\x00'

    If a :class:`function` is used as ``exists``::

        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     flag:     pak.Int8
        ...     optional: pak.Optional(pak.Int8, lambda p: p.flag == 3)
        ...
        >>> packet = MyPacket.unpack(b"\x03\x02")
        >>> packet
        MyPacket(flag=3, optional=2)
        >>> packet.pack()
        b'\x03\x02'
        >>>
        >>> packet = MyPacket.unpack(b"\x01")
        >>> packet
        MyPacket(flag=1, optional=None)
        >>> packet.pack()
        b'\x01'
    """

    @classmethod
    def _size(cls, value, *, ctx):
        if value is cls.STATIC_SIZE:
            return None

        if cls.exists(ctx.packet):
            return cls.elem_type.size(value, ctx=ctx)

        return 0

    @classmethod
    def _default(cls, *, ctx):
        if cls.exists(ctx.packet):
            return cls.elem_type.default(ctx=ctx)

        return None

    @classmethod
    def _unpack(cls, buf, *, ctx):
        if cls.exists(ctx.packet):
            return cls.elem_type.unpack(buf, ctx=ctx)

        return None

    @classmethod
    def _pack(cls, value, *, ctx):
        if cls.exists(ctx.packet):
            return cls.elem_type.pack(value, ctx=ctx)

        return b""

    @classmethod
    @Type.prepare_types
    def _call(cls, elem_type: Type, exists):
        exists_name = repr(exists)

        if isinstance(exists, str):
            attr   = exists
            exists = lambda packet: getattr(packet, attr)

        return cls.make_type(
            f"{cls.__qualname__}({elem_type.__qualname__}, {exists_name})",

            elem_type = elem_type,
            exists    = exists,
        )

# Set the appropriate naming for the 'Optional' specializations.

_PrefixChecked.__name__     = "PrefixChecked"
_PrefixChecked.__qualname__ = "Optional.PrefixChecked"
Optional.PrefixChecked      = _PrefixChecked

_Unchecked.__name__     = "Unchecked"
_Unchecked.__qualname__ = "Optional.Unchecked"
Optional.Unchecked      = _Unchecked

_FunctionChecked.__name__     = "FunctionChecked"
_FunctionChecked.__qualname__ = "Optional.FunctionChecked"
Optional.FunctionChecked      = _FunctionChecked

# Remove access to the specializations from
# their underline-prefixed names to stop
# them from showing up in the docs.

del _PrefixChecked
del _Unchecked
del _FunctionChecked
