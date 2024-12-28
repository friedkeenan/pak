"""Utilities for testing, exposed for users to use as well."""

from . import io
from . import util
from .types.type import NoStaticSizeError

__all__ = [
    "NO_DEFAULT",
    "type_behavior",
    "type_behavior_func",
    "type_behavior_async",
    "type_behavior_func_async",
    "type_behavior_both",
    "type_behavior_func_both",
    "packet_behavior",
    "packet_behavior_func",
    "packet_behavior_async",
    "packet_behavior_func_async",
    "packet_behavior_both",
    "packet_behavior_func_both",
]

#: An object passed to the :func:`type_behavior` functions
#: to indicate that a :class:`.Type` has no default value.
NO_DEFAULT = util.UniqueSentinel("NO_DEFAULT")

def _common_type_behavior(type_cls, *, static_size, alignment, default, ctx):
    # NOTE: We import 'pytest' locally so that pytest does not
    # become a required dependency of the library. Another solution
    # would be to make it so this module is not imported with
    # everything else, but I am not fond of that solution at all really.

    if static_size is None:
        import pytest

        with pytest.raises(NoStaticSizeError):
            type_cls.size(ctx=ctx)
    else:
        assert type_cls.size(type_cls.STATIC_SIZE, ctx=ctx) == static_size

    if alignment is None:
        import pytest

        with pytest.raises(TypeError):
            type_cls.alignment(ctx=ctx)
    else:
        assert type_cls.alignment(ctx=ctx) == alignment

        # We must have a static size if we are aligned.
        assert static_size is not None

        # The alignment cannot be negative.
        assert alignment >= 0

        if alignment == 0:
            # We must be the equivalent of 'EmptyType'
            # if we have an alignment of '0'.
            assert static_size == 0
        else:
            # Check that the alignment is a power of two.
            assert (alignment & (alignment - 1)) == 0

            # Check that the static size is a multiple of the alignment.
            assert static_size % alignment == 0

    if default is NO_DEFAULT:
        import pytest

        with pytest.raises(TypeError):
            type_cls.default(ctx=ctx)
    else:
        assert type_cls.default(ctx=ctx) == default

def type_behavior(type_cls, *values_and_data, static_size, alignment=None, default, ctx=None):
    r"""Asserts values marshal to and from expected data using a :class:`.Type`.

    When unpacking, the :meth:`.Type.unpack` method will be used.

    Whether the reported size from :meth:`.Type.size` for each value equals
    the size of the packed data is also asserted.

    .. seealso::

        :func:`type_behavior_func`
        :func:`type_behavior_async`
        :func:`type_behavior_both`

    Parameters
    ----------
    type_cls : subclass of :class:`.Type`
        The :class:`.Type` to test.
    *values_and_data : pair of any and :class:`bytes`
        The values and data to test.
    static_size : :class:`int` or ``None``
        The size of ``type_cls`` irrespective of any value.

        If ``None``, then ``type_cls`` should have no static size.
    alignment : :class:`int` or ``None``
        The alignment of ``type_cls``.

        If ``None``, then ``type_cls`` should have no alignment.

        If an ``alignment`` is provided, then a ``static_size``
        should be as well.
    default
        The default value of ``type_cls``.

        If :data:`NO_DEFAULT`, then ``type_cls`` should have no default value.
    ctx : :class:`.Type.Context` or ``None``
        The context for the :class:`.Type`.

    Examples
    --------
    >>> import pak
    >>> pak.test.type_behavior(
    ...     pak.UInt8,
    ...
    ...     (1, b"\x01"),
    ...     (2, b"\x02"),
    ...
    ...     static_size = 1,
    ...     alignment   = 1,
    ...     default     = 0,
    ... )
    """

    for value, data in values_and_data:
        data_from_value = type_cls.pack(value, ctx=ctx)
        value_from_data = type_cls.unpack(data, ctx=ctx)

        assert data_from_value == data,  f"{data_from_value=}; {data=}; {value=}"
        assert value_from_data == value, f"{value_from_data=}; {value=}; {data=}"

        size_from_value = type_cls.size(value, ctx=ctx)
        assert size_from_value == len(data), f"{size_from_value=}; {data=}; {value=}"

    _common_type_behavior(type_cls, static_size=static_size, alignment=alignment, default=default, ctx=ctx)

def type_behavior_func(*args, **kwargs):
    r"""Generates a function that calls :func:`type_behavior`.

    This should be used only if you just need to compare values
    and raw data, and the values should be compared using equality.
    For anything else, you should create your own function, potentially
    one which uses :func:`type_behavior`.

    Parameters
    ----------
    *args, **kwargs
        Forwarded to :func:`type_behavior`.

    Examples
    --------
    >>> import pak
    >>> test_uint8 = pak.test.type_behavior_func(
    ...     pak.UInt8,
    ...
    ...     (1, b"\x01"),
    ...     (2, b"\x02"),
    ...
    ...     static_size = 1,
    ...     alignment   = 1,
    ...     default     = 0,
    ... )
    >>> test_uint8()
    """

    return lambda: type_behavior(*args, **kwargs)

async def type_behavior_async(type_cls, *values_and_data, static_size, alignment=None, default, ctx=None):
    r"""Asserts values marshal to and from expected data using a :class:`.Type` asynchronously.

    When unpacking the raw data, the :meth:`.Type.unpack_async` method will be used.

    Whether the reported size from :meth:`.Type.size` for each value equals
    the size of the packed data is also asserted.

    .. seealso::

        :func:`type_behavior_func_async`
        :func:`type_behavior`
        :func:`type_behavior_both`

    Parameters
    ----------
    type_cls : subclass of :class:`.Type`
        The :class:`.Type` to test.
    *values_and_data : pair of any and :class:`bytes`
        The values and data to test.
    static_size : :class:`int` or ``None``
        The size of ``type_cls`` irrespective of any value.

        If ``None``, then ``type_cls`` should have no static size.
    alignment : :class:`int` or ``None``
        The alignment of ``type_cls``.

        If ``None``, then ``type_cls`` should have no alignment.

        If an ``alignment`` is provided, then a ``static_size``
        should be as well.
    default
        The default value of ``type_cls``.

        If :data:`NO_DEFAULT`, then ``type_cls`` should have no default value.
    ctx : :class:`.Type.Context` or ``None``
        The context for the :class:`.Type`.

    Examples
    --------
    >>> import pak
    >>> import asyncio
    >>> asyncio.run(pak.test.type_behavior_async(
    ...     pak.UInt8,
    ...
    ...     (1, b"\x01"),
    ...     (2, b"\x02"),
    ...
    ...     static_size = 1,
    ...     alignment   = 1,
    ...     default     = 0,
    ... ))
    """

    for value, data in values_and_data:
        data_from_value = type_cls.pack(value, ctx=ctx)
        value_from_data = await type_cls.unpack_async(data, ctx=ctx)

        assert data_from_value == data,  f"{data_from_value=}; {data=}; {value=}"
        assert value_from_data == value, f"{value_from_data=}; {value=}; {data=}"

        size_from_value = type_cls.size(value, ctx=ctx)
        assert size_from_value == len(data), f"{size_from_value=}; {data=}; {value=}"

    _common_type_behavior(type_cls, static_size=static_size, alignment=alignment, default=default, ctx=ctx)

def type_behavior_func_async(*args, **kwargs):
    r"""Generates a coroutine function that calls :func:`type_behavior_async`.

    This should be used only if you just need to compare values
    and raw data, and the values should be compared using equality.
    For anything else, you should create your own function, potentially
    one which uses :func:`type_behavior_async`.

    Parameters
    ----------
    *args, **kwargs
        Forwarded to :func:`type_behavior_async`.

    Examples
    --------
    >>> import pak
    >>> import asyncio
    >>> test_uint8 = pak.test.type_behavior_func_async(
    ...     pak.UInt8,
    ...
    ...     (1, b"\x01"),
    ...     (2, b"\x02"),
    ...
    ...     static_size = 1,
    ...     alignment   = 1,
    ...     default     = 0,
    ... )
    >>> asyncio.run(test_uint8())
    """

    async def tester():
        await type_behavior_async(*args, **kwargs)

    return tester

async def type_behavior_both(type_cls, *values_and_data, static_size, alignment=None, default, ctx=None):
    r"""Asserts values marshal to and from expected data using a :class:`.Type` both synchronously and asynchronously.

    When unpacking, both the :meth:`.Type.unpack` and
    :meth:`.Type.unpack_async` methods will be used.

    Whether the reported size from :meth:`.Type.size` for each value equals
    the size of the packed data is also asserted.

    .. seealso::

        :func:`type_behavior_func_both`

    Parameters
    ----------
    type_cls : subclass of :class:`.Type`
        The :class:`.Type` to test.
    *values_and_data : pair of any and :class:`bytes`
        The values and data to test.
    static_size : :class:`int` or ``None``
        The size of ``type_cls`` irrespective of any value.

        If ``None``, then ``type_cls`` should have no static size.
    alignment : :class:`int` or ``None``
        The alignment of ``type_cls``.

        If ``None``, then ``type_cls`` should have no alignment.

        If an ``alignment`` is provided, then a ``static_size``
        should be as well.
    default
        The default value of ``type_cls``.

        If :data:`NO_DEFAULT`, then ``type_cls`` should have no default value.
    ctx : :class:`.Type.Context` or ``None``
        The context for the :class:`.Type`.

    Examples
    --------
    >>> import pak
    >>> import asyncio
    >>> asyncio.run(pak.test.type_behavior_both(
    ...     pak.UInt8,
    ...
    ...     (1, b"\x01"),
    ...     (2, b"\x02"),
    ...
    ...     static_size = 1,
    ...     alignment   = 1,
    ...     default     = 0,
    ... ))
    """

    for value, data in values_and_data:
        data_from_value = type_cls.pack(value, ctx=ctx)

        assert data_from_value == data,  f"{data_from_value=}; {data=}; {value=}"

        value_from_data_sync  = type_cls.unpack(data, ctx=ctx)
        value_from_data_async = await type_cls.unpack_async(data, ctx=ctx)

        assert value_from_data_sync  == value, f"{value_from_data_sync=}; {value=}; {data=}"
        assert value_from_data_async == value, f"{value_from_data_async=}; {value=}; {data=}"

        size_from_value = type_cls.size(value, ctx=ctx)
        assert size_from_value == len(data), f"{size_from_value=}; {data=}; {value=}"

    _common_type_behavior(type_cls, static_size=static_size, alignment=alignment, default=default, ctx=ctx)

def type_behavior_func_both(*args, **kwargs):
    r"""Generates a coroutine function that calls :func:`type_behavior_both`.

    This should be used only if you just need to compare values
    and raw data, and the values should be compared using equality.
    For anything else, you should create your own function, potentially
    one which uses :func:`type_behavior_both`.

    Parameters
    ----------
    *args, **kwargs
        Forwarded to :func:`type_behavior_both`.

    Examples
    --------
    >>> import pak
    >>> import asyncio
    >>> test_uint8 = pak.test.type_behavior_func_both(
    ...     pak.UInt8,
    ...
    ...     (1, b"\x01"),
    ...     (2, b"\x02"),
    ...
    ...     static_size = 1,
    ...     alignment   = 1,
    ...     default     = 0,
    ... )
    >>> asyncio.run(test_uint8())
    """

    async def tester():
        await type_behavior_both(*args, **kwargs)

    return tester

def packet_behavior(*packets_and_data, ctx=None):
    r"""Asserts :class:`.Packet`\s marshal to and from expected data.

    When unpacking the raw data, the :meth:`.Packet.unpack` method will be used.

    Parameters
    ----------
    *packets_and_data : pair of :class:`.Packet` and :class:`bytes`
        The :class:`.Packet`\s and data to test.
    ctx : :class:`.Packet.Context`
        The context for the :class:`Packet`\s.

    Examples
    --------
    >>> import pak
    >>> class MyPacket(pak.Packet):
    ...     id = 1
    ...     field: pak.UInt8
    ...     class Header(pak.Packet.Header):
    ...         id: pak.UInt8
    ...
    >>> pak.test.packet_behavior(
    ...     (MyPacket(field=2), b"\x01\x02"),
    ...     (MyPacket(field=3), b"\x01\x03"),
    ... )
    """

    for packet, data in packets_and_data:
        data_file = util.file_object(data)

        header_from_packet = packet.header(ctx=ctx)
        header_from_data   = packet.Header.unpack(data_file, ctx=ctx)

        assert header_from_packet == header_from_data, f"{data=}; {packet=}"

        data_from_packet = packet.pack(ctx=ctx)
        packet_from_data = packet.unpack(data_file, ctx=ctx)

        assert data_from_packet == data,   f"{data_from_packet=}; {data=}; {packet=}"
        assert packet_from_data == packet, f"{packet_from_data=}; {packet=}; {data=}"

def packet_behavior_func(*args, **kwargs):
    r"""Generates a function that calls :func:`packet_behavior`.

    This should be used only if you just need to compare :class:`.Packet`\s
    and raw data, and the :class:`.Packet`\s should be compared using equality.
    For anything else, you should create your own function, potentially one which
    uses :func:`packet_behavior`.

    Parameters
    ----------
    *args, **kwargs
        Forwarded to :func:`packet_behavior`.

    Examples
    --------
    >>> import pak
    >>> class MyPacket(pak.Packet):
    ...     id = 1
    ...     field: pak.UInt8
    ...     class Header(pak.Packet.Header):
    ...         id: pak.UInt8
    ...
    >>> test_my_packet = pak.test.packet_behavior_func(
    ...     (MyPacket(field=2), b"\x01\x02"),
    ...     (MyPacket(field=3), b"\x01\x03"),
    ... )
    >>> test_my_packet()
    """

    return lambda: packet_behavior(*args, **kwargs)

async def packet_behavior_async(*packets_and_data, ctx=None):
    r"""Asserts :class:`.Packet`\s marshal to and from expected data asynchronously.

    When unpacking the raw data, the :meth:`.Packet.unpack_async` method will be used.

    Parameters
    ----------
    *packets_and_data : pair of :class:`.Packet` and :class:`bytes`
        The :class:`.Packet`\s and data to test.
    ctx : :class:`.Packet.Context`
        The context for the :class:`Packet`\s.

    Examples
    --------
    >>> import pak
    >>> import asyncio
    >>> class MyPacket(pak.Packet):
    ...     id = 1
    ...     field: pak.UInt8
    ...     class Header(pak.Packet.Header):
    ...         id: pak.UInt8
    ...
    >>> asyncio.run(pak.test.packet_behavior_async(
    ...     (MyPacket(field=2), b"\x01\x02"),
    ...     (MyPacket(field=3), b"\x01\x03"),
    ... ))
    """

    for packet, data in packets_and_data:
        data_reader = io.ByteStreamReader(data)

        header_from_packet = packet.header(ctx=ctx)
        header_from_data   = await packet.Header.unpack_async(data_reader, ctx=ctx)

        assert header_from_packet == header_from_data, f"{data=}; {packet=}"

        data_from_packet = packet.pack(ctx=ctx)
        packet_from_data = await packet.unpack_async(data_reader, ctx=ctx)

        assert data_from_packet == data,   f"{data_from_packet=}; {data=}; {packet=}"
        assert packet_from_data == packet, f"{packet_from_data=}; {packet=}; {data=}"

def packet_behavior_func_async(*args, **kwargs):
    r"""Generates a coroutine function that calls :func:`packet_behavior_async`.

    This should be used only if you just need to compare :class:`.Packet`\s
    and raw data, and the :class:`.Packet`\s should be compared using equality.
    For anything else, you should create your own function, potentially one which
    uses :func:`packet_behavior_async`.

    Parameters
    ----------
    *args, **kwargs
        Forwarded to :func:`packet_behavior_async`.

    Examples
    --------
    >>> import pak
    >>> import asyncio
    >>> class MyPacket(pak.Packet):
    ...     id = 1
    ...     field: pak.UInt8
    ...     class Header(pak.Packet.Header):
    ...         id: pak.UInt8
    ...
    >>> test_my_packet = pak.test.packet_behavior_func_async(
    ...     (MyPacket(field=2), b"\x01\x02"),
    ...     (MyPacket(field=3), b"\x01\x03"),
    ... )
    >>> asyncio.run(test_my_packet())
    """

    async def tester():
        await packet_behavior_async(*args, **kwargs)

    return tester

async def packet_behavior_both(*packets_and_data, ctx=None):
    r"""Asserts :class:`.Packet`\s marshal to and from expected data asynchronously.

    When unpacking, both the :meth:`.Packet.unpack` and
    :meth:`.Packet.unpack_async` methods will be used.

    Parameters
    ----------
    *packets_and_data : pair of :class:`.Packet` and :class:`bytes`
        The :class:`.Packet`\s and data to test.
    ctx : :class:`.Packet.Context`
        The context for the :class:`Packet`\s.

    Examples
    --------
    >>> import pak
    >>> import asyncio
    >>> class MyPacket(pak.Packet):
    ...     id = 1
    ...     field: pak.UInt8
    ...     class Header(pak.Packet.Header):
    ...         id: pak.UInt8
    ...
    >>> asyncio.run(pak.test.packet_behavior_both(
    ...     (MyPacket(field=2), b"\x01\x02"),
    ...     (MyPacket(field=3), b"\x01\x03"),
    ... ))
    """

    for packet, data in packets_and_data:
        data_file   = util.file_object(data)
        data_reader = io.ByteStreamReader(data)

        header_from_packet = packet.header(ctx=ctx)

        header_from_data_sync  = packet.Header.unpack(data_file, ctx=ctx)
        header_from_data_async = await packet.Header.unpack_async(data_reader, ctx=ctx)

        assert header_from_packet == header_from_data_sync,  f"{data=}; {packet=}"
        assert header_from_packet == header_from_data_async, f"{data=}; {packet=}"

        data_from_packet = packet.pack(ctx=ctx)

        assert data_from_packet == data, f"{data_from_packet=}; {data=}; {packet=}"

        packet_from_data_sync  = packet.unpack(data_file, ctx=ctx)
        packet_from_data_async = await packet.unpack_async(data_reader, ctx=ctx)

        assert packet_from_data_sync  == packet, f"{packet_from_data_sync=}; {packet=}; {data=}"
        assert packet_from_data_async == packet, f"{packet_from_data_async=}; {packet=}; {data=}"

def packet_behavior_func_both(*args, **kwargs):
    r"""Generates a function that calls :func:`packet_behavior_both`.

    This should be used only if you just need to compare :class:`.Packet`\s
    and raw data, and the :class:`.Packet`\s should be compared using equality.
    For anything else, you should create your own function, potentially one which
    uses :func:`packet_behavior_both`.

    Parameters
    ----------
    *args, **kwargs
        Forwarded to :func:`packet_behavior_both`.

    Examples
    --------
    >>> import pak
    >>> import asyncio
    >>> class MyPacket(pak.Packet):
    ...     id = 1
    ...     field: pak.UInt8
    ...     class Header(pak.Packet.Header):
    ...         id: pak.UInt8
    ...
    >>> test_my_packet = pak.test.packet_behavior_func_both(
    ...     (MyPacket(field=2), b"\x01\x02"),
    ...     (MyPacket(field=3), b"\x01\x03"),
    ... )
    >>> asyncio.run(test_my_packet())
    """

    async def tester():
        await packet_behavior_both(*args, **kwargs)

    return tester
