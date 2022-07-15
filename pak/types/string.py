r"""String :class:`~.Type`\s."""

import codecs

from .. import util
from .type import Type

__all__ = [
    "StaticString",
    "PrefixedString",
    "Char",
]

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

# TODO: Do we really want this Type?
# It's very niche but hard to get right and it may be nice
# to have it special cased for 'Array'.
class Char(Type):
    r"""A single character.

    .. warning::

        This is a more niche :class:`~.Type` than
        :class:`StaticString` or :class:`PrefixedString`.
        Before using :class:`Char`, make sure that those
        :class:`~.Type`\s or one you make yourself would
        not work better for your needs.

        This :class:`~.Type` can have different sizes depending
        on the encoding, because conceptually **it represents
        a codepoint**.

    Can be used with :class:`~.Array`, for which
    this :class:`~.Type` is special-cased to produce
    a :class:`str` value.

    By default, ASCII is used as the encoding. This is
    to ensure that by default, one :class:`Char` maps to
    one byte of raw data.

    .. note::

        ``Char[None]`` will read to the end of the buffer
        as other :class:`~.Array`\s will, **not**
        just to the next null-byte.

    Parameters
    ----------
    encoding : :class:`str`
        The encoding to use to encode/decode data.
    """

    _default = "a"

    encoding = "ascii"

    @classmethod
    def decode(cls, buf, *, chars=-1):
        """Decodes a string from raw data.

        Uses the class's encoding to decode the data.

        Parameters
        ----------
        buf : file object
            The file object containing the raw data.
        chars : :class:`int`
            How many characters to decode.

        Returns
        -------
        :class:`str`
            The decoded string.
        """

        reader = codecs.getreader(cls.encoding)(buf)
        string = reader.read(chars=chars)

        if len(string) < chars:
            raise util.BufferOutOfDataError("Reading characters failed")

        return string

    @classmethod
    def encode(cls, string):
        """Encodes a string to raw data.

        Uses the class's encoding to encode the string.

        Parameters
        ----------
        string : :class:`str`
            The string to encode.

        Returns
        -------
        :class:`bytes`
            The encoded data.
        """

        return string.encode(cls.encoding)

    @classmethod
    def _size(cls, value, *, ctx):
        # TODO: See if there's a more generic way to do this.

        if cls.encoding == "ascii":
            return 1

        return None

    @classmethod
    def _alignment(cls, *, ctx):
        # TODO: See if there's a more generic way to do this.

        if cls.encoding == "ascii":
            return 1

        return None

    @classmethod
    def _unpack(cls, buf, *, ctx):
        return cls.decode(buf, chars=1)

    @classmethod
    def _pack(cls, value, *, ctx):
        return cls.encode(value[:1])

    @classmethod
    def _call(cls, encoding):
        return cls.make_type(
            f"{cls.__qualname__}({repr(encoding)})",

            encoding = encoding,
        )
