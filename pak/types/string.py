r""":class:`.Type`\s for strings."""

import codecs

from .. import util
from .type import Type

__all__ = [
    "PrefixedString",
    "TerminatedString",
    "StaticTerminatedString",
]

# NOTE: We default to the 'replace' error handling
# mode in these string types. 'strict' is the normal
# default error handling mode, however it may not be
# desirable often to raise an exception on decoding
# errors in the domains Pak is used in.
#
# The 'surrogateescape' error mode may be more appropriate.
#
# This may warrant more investigation.

class PrefixedString(Type):
    """A string prefixed by the length of its encoded data.

    Parameters
    ----------
    prefix : typelike
        The :class:`.Type` which prefixes the string data
        and represents the length of the string.

        The prefixed length represents the amount of **bytes**
        the string data takes up.

        .. note::

            This does not include terminator characters such as a null-terminator.
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
    async def _unpack_async(cls, reader, *, ctx):
        length = await cls.prefix.unpack_async(reader, ctx=ctx)
        data   = await reader.readexactly(length)

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
            errors   = errors,
        )

class TerminatedString(Type):
    """A string that is read until a terminator character is reached.

    By default the terminator character is a null-terminator.

    A :exc:`util.BufferOutOfDataError <.BufferOutOfDataError>` is raised when
    unpacking if no terminator can be found.

    Parameters
    ----------
    encoding : :class:`str`
        The encoding to encode/decode the data.

        If ``None``, then the value of the :attr:`encoding`
        attribute is used.
    terminator : :class:`str`
        A single character indicating when string data
        has concluded.

        If ``None`` the value of the :attr:`terminator`
        attribute is used.
    errors : :class:`str`
        The error handling scheme for encoding/decoding errors.

        If ``None``, then the value of the :attr:`errors`
        attribute is used.
    """

    _default = ""

    encoding   = "utf-8"
    terminator = "\0"
    errors     = "replace"

    # We must set this here because '__init_subclass__' will not get called
    # for this parent class.
    _incremental_decoder = codecs.lookup(encoding).incrementaldecoder(errors=errors)

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if len(cls.terminator) != 1:
            raise ValueError(f"Terminator {repr(cls.terminator)} for '{cls.__qualname__}' is not of length 1")

        # We don't use 'codecs.incrementaldecoder' so we can pass the 'errors' argument.
        cls._incremental_decoder = codecs.lookup(cls.encoding).incrementaldecoder(errors=cls.errors)

    @classmethod
    def _unpack(cls, buf, *, ctx):
        string = ""

        while True:
            byte = buf.read(1)
            if byte == b"":
                raise util.BufferOutOfDataError("Buffer ran out of string data")

            decoded_character = cls._incremental_decoder.decode(byte)
            if decoded_character == "":
                continue

            if decoded_character == cls.terminator:
                cls._incremental_decoder.decode(b"", final=True)

                return string

            string += decoded_character

    @classmethod
    async def _unpack_async(cls, reader, *, ctx):
        string = ""

        while True:
            byte = await reader.readexactly(1)

            decoded_character = cls._incremental_decoder.decode(byte)
            if decoded_character == "":
                continue

            if decoded_character == cls.terminator:
                cls._incremental_decoder.decode(b"", final=True)

                return string

            string += decoded_character

    @classmethod
    def _pack(cls, value, *, ctx):
        value += cls.terminator

        return value.encode(cls.encoding, errors=cls.errors)

    # NOTE: There could be potential optimizations we could make
    # for when terminated strings are used in an array, namely
    # for unsized arrays, where we could read the whole buffer,
    # decode it, and then split the string on the terminator.
    #
    # I would want measurements to ensure that it would actually
    # be an optimization though.

    @classmethod
    def _call(cls, *, encoding=None, terminator=None, errors=None):
        if encoding is None:
            encoding = cls.encoding

        if terminator is None:
            terminator = cls.terminator

        if errors is None:
            errors = cls.errors

        return cls.make_type(
            cls.__qualname__,

            encoding   = encoding,
            terminator = terminator,
            errors     = errors,
        )

# NOTE: We do not implement both a terminated and non-terminated
# version of 'StaticString'.
#
# I feel as if almost all instances of a statically sized string would
# be from a language such as C which would be expecting a null-terminator
# in say a 'char' array struct member. Additionally, without a terminator,
# all strings would have to be the same length, instead of just having
# to fit within the same buffer.
#
# However, if it is found that a non-terminated version of this is
# desirable and has widespread enough utility, then I would be willing
# to include such a Type.
class StaticTerminatedString(Type):
    """A string with a static size, terminated by a certain character.

    By default the terminator character is a null-terminator.

    A :exc:`ValueError` is raised when unpacking if
    no terminator is found in the data. Additionally a
    :exc:`util.BufferOutOfDataError <.BufferOutOfDataError>`
    is raised if the buffer doesn't contain the static size.

    Additionally, a :exc:`ValueError` is raised when packing
    if the to-be-packed value is too long for the static size.

    Parameters
    ----------
    size : :class:`int`
        The static size of the raw data containing the string.

        This size is in **bytes**.

        .. warning::

            The size should contain the terminator.
    encoding : :class:`str` or ``None``
        The encoding to use to encode/decode the data.

        If ``None``, then the value of the :attr:`encoding`
        attribute is used.
    terminator : :class:`str`
        A single character indicating when string data
        has concluded.

        If ``None`` the value of the :attr:`terminator`
        attribute is used.
    errors : :class:`str`
        The error handling scheme for encoding/decoding errors.

        If ``None``, then the value of the :attr:`errors`
        attribute is used.
    alignment : :class:`int` or ``None``
        The alignment of the string data.

        If ``None`` and ``encoding`` is ``None`` or the
        original encoding, ``alignment`` will be assumed
        to be the same as the original alignment.
    """

    _size      = None
    _alignment = 1
    _default   = ""

    encoding   = "utf-8"
    terminator = "\0"
    errors     = "replace"

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if len(cls.terminator) != 1:
            raise ValueError(f"Terminator {repr(cls.terminator)} for '{cls.__qualname__}' is not of length 1")

        # We don't use 'codecs.incrementaldecoder' so we can pass the 'errors' argument.
        cls._incremental_decoder = codecs.lookup(cls.encoding).incrementaldecoder(errors=cls.errors)

    @classmethod
    def _unpack(cls, buf, *, ctx):
        # We must use an incremental decoder to decode our string data
        # so that the garbage data after the terminator plays nicely
        # with the 'errors' attribute.

        buffer_size = cls.size(ctx=ctx)

        data = bytearray(buf.read(buffer_size))
        if len(data) < buffer_size:
            raise util.BufferOutOfDataError("Could not read the full string buffer")

        string = ""

        while True:
            byte = bytes([data.pop(0)])
            decoded_character = cls._incremental_decoder.decode(byte)
            if decoded_character == "":
                continue

            if decoded_character == cls.terminator:
                cls._incremental_decoder.decode(b"", final=True)

                return string

            if len(data) <= 0:
                raise ValueError("Could not find terminator in string data")

            string += decoded_character

    @classmethod
    async def _unpack_async(cls, reader, *, ctx):
        # We must use an incremental decoder to decode our string data
        # so that the garbage data after the terminator plays nicely
        # with the 'errors' attribute.

        buffer_size = cls.size(ctx=ctx)

        data = bytearray(await reader.readexactly(buffer_size))

        string = ""
        while True:
            byte = bytes([data.pop(0)])
            decoded_character = cls._incremental_decoder.decode(byte)
            if decoded_character == "":
                continue

            if decoded_character == cls.terminator:
                cls._incremental_decoder.decode(b"", final=True)

                return string

            if len(data) <= 0:
                raise ValueError("Could not find terminator in string data")

            string += decoded_character

    @classmethod
    def _pack(cls, value, *, ctx):
        value += cls.terminator

        data   = value.encode(cls.encoding, errors=cls.errors)
        length = len(data)

        if length > cls.size(ctx=ctx):
            raise ValueError(f"Value is too large to pack for '{cls.__qualname__}': {repr(value)}")

        return data + b"\x00" * (cls.size(ctx=ctx) - length)

    @classmethod
    def _call(cls, size, *, encoding=None, terminator=None, errors=None, alignment=None):
        if encoding is None:
            encoding = cls.encoding

        if alignment is None and encoding == cls.encoding:
            # If the encoding is the same, we can assume
            # the alignment is the same as well.
            alignment = cls._alignment

        if terminator is None:
            terminator = cls.terminator

        if errors is None:
            errors = cls.errors

        return cls.make_type(
            f"StaticTerminatedString({size})",

            _size      = size,
            _alignment = alignment,
            encoding   = encoding,
            terminator = terminator,
            errors     = errors,
        )
