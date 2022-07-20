r"""String :class:`~.Type`\s."""

import codecs

from .. import util
from .type import Type

__all__ = [
    "StaticString",
    "PrefixedString",
]

# NOTE: We do not implement both a null-terminated and non-null-terminated
# version of 'StaticString'.
#
# I feel as if almost all instances of a statically sized string would
# be from a language such as C which would be expecting a null terminator
# in say a 'char' array struct member. Additionally, without a null terminator,
# all strings would have to be the same length, instead of just having
# to fit within the same buffer.
#
# However, if it is found that a non-null-terminated version of this is
# desirable and has widespread enough utility, then I would be willing
# to include such a Type.
class StaticString(Type):
    """A null-terminated string with a static size.

    A :exc:`ValueError` is raised when unpacking if
    no null terminator is found in the data.

    Additionally, a :exc:`ValueError` is raised when packing
    if the to-be-packed value is too long for the static size.

    Parameters
    ----------
    size : :class:`int`
        The static size of the raw data containing the string.

        This size is in **bytes**.

        .. warning::

            The size should contain the null terminator.
    encoding : :class:`str` or ``None``
        The encoding to use to encode/decode the data.

        If ``None``, then the value of the :attr:`encoding`
        attribute is used.
    errors : :class:`str`
        The error handling scheme for encoding/decoding errors.

        If ``None``, then the value of the :attr:`errors`
        attribute is used.
    """

    _size      = None
    _alignment = 1
    _default   = ""

    encoding = "utf-8"
    errors   = "replace"

    @classmethod
    def _unpack(cls, buf, *, ctx):
        data = buf.read(cls.size(ctx=ctx))

        # Decode then chop off the null terminator.
        chopped = data.decode(cls.encoding, errors=cls.errors).split("\0", 1)
        if len(chopped) == 1 and chopped[0] != "":
            raise ValueError(f"No null terminator found when unpacking '{cls.__qualname__}'")

        return chopped[0]

    @classmethod
    def _pack(cls, value, *, ctx):
        value += "\0"

        data   = value.encode(cls.encoding, errors=cls.errors)
        length = len(data)

        if length > cls.size(ctx=ctx):
            raise ValueError(f"Value is too large to pack for '{cls.__qualname__}': {repr(value)}")

        return data + b"\x00" * (cls.size(ctx=ctx) - length)

    @classmethod
    def _call(cls, size, *, encoding=None, errors=None):
        if encoding is None:
            encoding = cls.encoding

        if errors is None:
            errors = cls.errors

        return cls.make_type(
            f"StaticString({size})",

            _size    = size,
            encoding = encoding,
        )

class PrefixedString(Type):
    """A string prefixed by its length.

    Parameters
    ----------
    prefix : typelike
        The :class:`~.Type` which prefixes the string data
        and represents the length of the string.

        The prefixed length represents the amount of **bytes**
        the string data takes up.

        .. note::

            This does not include null terminators.
    encoding : :class:`str` or ``None``
        The encoding to encode/decode the data.

        If ``None``, then the value of the :attr:`encoding`
        attribute is used.
    errors : :class:`str`
        The error handling scheme for encoding/decoding errors.

        If ``None``, then the value of the :attr:`errors`
        attribute is used.
    """

    _default = ""

    prefix   = None
    encoding = "utf-8"
    errors   = "replace"

    @classmethod
    def _size(cls, value, *, ctx):
        if value is cls.STATIC_SIZE:
            return None

        return cls.prefix.size(len(value), ctx=ctx) + len(value.encode(cls.encoding, errors=cls.errors))

    @classmethod
    def _unpack(cls, buf, *, ctx):
        length = cls.prefix.unpack(buf, ctx=ctx)
        data   = buf.read(length)

        return data.decode(cls.encoding, errors=cls.errors)

    @classmethod
    def _pack(cls, value, *, ctx):
        data = value.encode(cls.encoding, errors=cls.errors)

        return cls.prefix.pack(len(data), ctx=ctx) + data

    @classmethod
    @Type.prepare_types
    def _call(cls, prefix: Type, *, encoding=None, errors=None):
        if encoding is None:
            encoding = cls.encoding

        if errors is None:
            errors = cls.errors

        return cls.make_type(
            f"PrefixedString({prefix.__qualname__})",

            prefix   = prefix,
            encoding = encoding,
        )
