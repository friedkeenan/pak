r"""Enumeration :class:`.Type`\s."""

from .. import util
from .type import Type

__all__ = [
    "Enum",
    "EnumOr",
]

class Enum(Type):
    r"""Maps a :class:`.Type` to an :class:`enum.Enum`.

    The default value of the :class:`.Type` is the first
    member of the enum.

    Parameters
    ----------
    elem_type : typelike
        The underlying :class:`.Type`.
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
    >>> EnumType.unpack(b"\x03") is pak.Enum.INVALID
    True
    """

    elem_type = None
    enum_type = None

    # NOTE: I feel this is the best API we can manage in order
    # to handle invalid enum values, but there are possible issues:
    #
    # - By collapsing every invalid enum value down to a single
    #   object, you lose the information of what the offending
    #   value was. "Good" code should not be using invalid enum
    #   values, however this may be a subpar situation for
    #   debugging/research. Perhaps we could expose more information
    #   in a sort of "debug" mode of the library, where we could
    #   e.g. log the offending value. That may be part of a larger
    #   todo of logging generally though. This issue is also
    #   mitigated by the existence of 'EnumOr'.
    #
    # - Also by collapsing every invalid enum value down to a
    #   single object, we rob the ability to pack invalid enum
    #   values. Users should not be trying to pack invalid enum
    #   values, and this matches with other Types which cannot
    #   pack values they were not meant to (e.g. Int8 can't pack
    #   strings). This however does create an awkward situation
    #   where an Enum can return a value from unpacking which then
    #   can't be packed again. I lean towards this being fine,
    #   but there is to consider that for something like a proxy,
    #   which does not control either end of its protocol and may
    #   just simply be forwarding on packets, a change in its
    #   proxied protocol to add a new valid enum value could then
    #   break the proxy, requiring the addition of the new valid
    #   enum value. I do not presently feel very sympathetic to
    #   this issue, and lean towards that if a protocol changes,
    #   then your pak specification should simply be updated accordingly.
    INVALID = util.UniqueSentinel("INVALID")

    @classmethod
    def _size(cls, value, *, ctx):
        if value is cls.STATIC_SIZE or value is cls.INVALID:
            return cls.elem_type.size(ctx=ctx)

        return cls.elem_type.size(value.value, ctx=ctx)

    @classmethod
    def _alignment(cls, *, ctx):
        return cls.elem_type.alignment(ctx=ctx)

    @classmethod
    def _default(cls, *, ctx):
        # Get the first member of the enum type.
        return next(iter(cls.enum_type.__members__.values()))

    @classmethod
    def _unpack(cls, buf, *, ctx):
        value = cls.elem_type.unpack(buf, ctx=ctx)

        try:
            return cls.enum_type(value)
        except ValueError:
            return cls.INVALID

    @classmethod
    def _pack(cls, value, *, ctx):
        if value is cls.INVALID:
            raise ValueError(f"Cannot pack invalid value for {cls.__qualname__}")

        return cls.elem_type.pack(value.value, ctx=ctx)

    @classmethod
    @Type.prepare_types
    def _call(cls, elem_type: Type, enum_type):
        return cls.make_type(
            f"{cls.__qualname__}({elem_type.__qualname__}, {enum_type.__qualname__})",

            elem_type = elem_type,
            enum_type = enum_type,
        )

class EnumOr(Type):
    r"""Maps a :class:`.Type` to an :class:`enum.Enum` if possible.

    This :class:`.Type` should be used for when values only
    *potentially* have semantic meaning. This could be for
    instance when a client sends some user-sourced input to
    the server, which *generally* should be of a set of
    expected values, i.e. the :class:`enum.Enum` in question,
    but under valid operation could still be some value
    *outside* of that expected set. Like if say a client
    is expected to send ``"red"``, ``"blue"``, or ``"green"``
    to the server, but the user is capable of sending some
    other string like ``"pink"``.

    The default value of the :class:`.Type` is the first
    member of the enum.

    Parameters
    ----------
    elem_type : typelike
        The underlying :class:`.Type`.
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
    >>> EnumOrType = pak.EnumOr(pak.Int8, MyEnum)
    >>> EnumOrType
    <class 'pak.types.enum.EnumOr(Int8, MyEnum)'>
    >>> EnumOrType.default()
    <MyEnum.A: 1>
    >>> EnumOrType.pack(MyEnum.B)
    b'\x02'
    >>> EnumOrType.unpack(b"\x02")
    <MyEnum.B: 2>
    >>> EnumOrType.pack(3)
    b'\x03'
    >>> EnumOrType.unpack(b"\x03")
    3
    """

    elem_type = None
    enum_type = None

    # NOTE: We could add a '__set__' method to change
    # raw values that are valid enum values into said
    # enum values, but I feel like that could make user
    # code potentially confusing, e.g. if the user sets
    # a packet field to '1' and then later they check if
    # it equals '1', then that would fail because it would
    # actually be transformed into say 'MyEnum.One', and
    # that transformation is not obvious to the user.

    @classmethod
    def _raw_value(cls, value):
        if isinstance(value, cls.enum_type):
            return value.value

        return value

    @classmethod
    def _size(cls, value, *, ctx):
        # NOTE: We don't need to special case static size.
        return cls.elem_type.size(cls._raw_value(value), ctx=ctx)

    @classmethod
    def _alignment(cls, *, ctx):
        return cls.elem_type.alignment(ctx=ctx)

    @classmethod
    def _default(cls, *, ctx):
        return next(iter(cls.enum_type.__members__.values()))

    @classmethod
    def _unpack(cls, buf, *, ctx):
        value = cls.elem_type.unpack(buf, ctx=ctx)

        try:
            return cls.enum_type(value)
        except ValueError:
            return value

    @classmethod
    def _pack(cls, value, *, ctx):
        return cls.elem_type.pack(cls._raw_value(value), ctx=ctx)

    @classmethod
    @Type.prepare_types
    def _call(cls, elem_type: Type, enum_type):
        return cls.make_type(
            f"{cls.__qualname__}({elem_type.__qualname__}, {enum_type.__qualname__})",

            elem_type = elem_type,
            enum_type = enum_type,
        )
