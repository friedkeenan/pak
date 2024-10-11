"""Utilities for testing, exposed for users to use as well."""

from . import io
from . import util
from .types.type import NoStaticSizeError

__all__ = [
    "NO_DEFAULT",
    "type_behavior",
    "type_behavior_async",
    "type_behavior_func",
    "packet_behavior",
    "packet_behavior_func",
]

#: An object passed to :func:`type_behavior` or :func:`type_behavior_async`
#: to indicate a :class:`.Type` has no default value.
NO_DEFAULT = util.UniqueSentinel("NO_DEFAULT")

def _common_type_behavior(type_cls, *, static_size, alignment, default, ctx):
    if static_size is None:
        import pytest

        with pytest.raises(NoStaticSizeError):
            type_cls.size(ctx=ctx)
    else:
        assert type_cls.size(type_cls.STATIC_SIZE, ctx=ctx) == static_size

    # We import 'pytest' locally so that pytest does not become a
    # required dependency of the library. Another solution would
    # be to make it so this module is not imported with everything
    # else, but I am not fond of that solution at all really.
    if alignment is None:
        import pytest

        with pytest.raises(TypeError):
            type_cls.alignment(ctx=ctx)
    else:
        assert static_size is not None
        assert type_cls.alignment(ctx=ctx) == alignment

        # Check that 'alignment' is a power of two.
        assert alignment != 0
        assert (alignment & (alignment - 1)) == 0

    if default is NO_DEFAULT:
        import pytest

        with pytest.raises(TypeError):
            type_cls.default(ctx=ctx)
    else:
        assert type_cls.default(ctx=ctx) == default

def type_behavior(type_cls, *values_and_data, static_size, alignment=None, default, ctx=None):
    r"""Asserts values marshal to and from expected data using a :class:`.Type`.

    Whether the reported size from :meth:`.Type.size` for each value equals
    the size of the packed data is also asserted.

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

        assert data_from_value == data,  f"data_from_value={data_from_value}; data={data}; value={value}"
        assert value_from_data == value, f"value_from_data={value_from_data}; value={value}; data={data}"

        size_from_value = type_cls.size(value, ctx=ctx)
        assert size_from_value == len(data), f"size_from_value={size_from_value}; data={data}; value={value}"

    _common_type_behavior(type_cls, static_size=static_size, alignment=alignment, default=default, ctx=ctx)

async def type_behavior_async(type_cls, *values_and_data, static_size, alignment=None, default, ctx=None):
    r"""Asserts values marshal to and from expected data using a :class:`.Type` asynchronously.

    .. note::

        If ``type_cls`` has synchronous unpacking, then
        that will be tested as well. You therefore don't
        need to also call :func:`type_behavior` to test
        synchronous behavior.

    Whether the reported size from :meth:`.Type.size` for each value equals
    the size of the packed data is also asserted.

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

    has_sync_unpacking = type_cls.has_synchronous_unpacking()

    for value, data in values_and_data:
        data_from_value = type_cls.pack(value, ctx=ctx)

        async_value_from_data = await type_cls.unpack_async(io.ByteStreamReader(data), ctx=ctx)

        assert data_from_value       == data,  f"data_from_value={data_from_value}; data={data}; value={value}"
        assert async_value_from_data == value, f"async_value_from_data={async_value_from_data}; value={value}; data={data}"

        if has_sync_unpacking:
            sync_value_from_data = type_cls.unpack(data, ctx=ctx)

            assert data_from_value      == data,  f"data_from_value={data_from_value}; data={data}; value={value}"
            assert sync_value_from_data == value, f"sync_value_from_data={sync_value_from_data}; value={value}; data={data}"

        size_from_value = type_cls.size(value, ctx=ctx)
        assert size_from_value == len(data), f"size_from_value={size_from_value}; data={data}; value={value}"

    _common_type_behavior(type_cls, static_size=static_size, alignment=alignment, default=default, ctx=ctx)

def type_behavior_func(type_cls, *args, **kwargs):
    r"""Generates a function that calls :func:`type_behavior` or :func:`type_behavior_async`.

    This should be used only if you just need to compare values
    and raw data, and the values should be compared using equality.
    For anything else, you should create your own function, potentially
    one which uses :func:`type_behavior`.

    When ``type_cls`` has asynchronous unpacking, then the
    generated function will be a coroutine function that
    properly tests both asynchronous and synchronous behavior,
    if applicable.

    Parameters
    ----------
    type_cls : subclass of :class:`.Type`
        The :class:`.Type` to test.
    *args, **kwargs
        Forwarded to :func:`type_behavior` or :func:`type_behavior_async`.

    Returns
    -------
    :class:`function`
        The proper function that will test the :class:`.Type`.

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
    """

    if not type_cls.has_asynchronous_unpacking():
        return lambda: type_behavior(type_cls, *args, **kwargs)

    async def tester():
        await type_behavior_async(type_cls, *args, **kwargs)

    return tester

def packet_behavior(*packets_and_data, ctx=None):
    r"""Asserts :class:`.Packet`\s marshal to and from expected data.

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

        assert header_from_packet == header_from_data, f"data={data}, packet={packet}"

        data_from_packet = packet.pack(ctx=ctx)
        packet_from_data = packet.unpack(data_file, ctx=ctx)

        assert data_from_packet == data,   f"data_from_packet={data_from_packet}; data={data}; packet={packet}"
        assert packet_from_data == packet, f"packet_from_data={packet_from_data}; packet={packet}; data={data}"

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
