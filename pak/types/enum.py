r"""Enumeration :class:`~.Type`\s."""

from .type import Type

__all__ = [
    "Enum",
]

class Enum(Type):
    r"""Maps an :class:`enum.Enum` to a :class:`~.Type`.

    The default value of the :class:`~.Type` is the first
    member of the enum.

    .. warning::
        If a value that is not in the enum is unpacked, an
        error will be raised.

    Parameters
    ----------
    elem_type : typelike
        The underlying :class:`~.Type`.
    enum_type : subclass of :class:`enum.Enum`
        The enum to map values to.

    Examples
    --------
    >>> import enum
    >>> import pak
    >>> class MyEnum(enum.Enum):
    ...     A = 1
    ...     B = 2
    ...
    >>> EnumType = pak.Enum(pak.Int8, MyEnum)
    >>> EnumType
    <class 'pak.types.enum.Enum(Int8, MyEnum)'>
    >>> EnumType.default()
    <MyEnum.A: 1>
    >>> EnumType.pack(MyEnum.B)
    b'\x02'
    >>> EnumType.unpack(b"\x02")
    <MyEnum.B: 2>
    """

    elem_type = None
    enum_type = None

    @classmethod
    def _default(cls, *, ctx):
        # Get the first member of the enum type.
        return next(iter(cls.enum_type.__members__.values()))

    @classmethod
    def _unpack(cls, buf, *, ctx):
        return cls.enum_type(cls.elem_type.unpack(buf, ctx=ctx))

    @classmethod
    def _pack(cls, value, *, ctx):
        return cls.elem_type.pack(value.value, ctx=ctx)

    @classmethod
    @Type.prepare_types
    def _call(cls, elem_type: Type, enum_type):
        return cls.make_type(
            f"{cls.__name__}({elem_type.__name__}, {enum_type.__name__})",

            elem_type = elem_type,
            enum_type = enum_type,
        )
