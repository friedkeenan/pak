"""Utilities for testing, exposed for users to use as well."""

from . import util

__all__ = [
    "assert_type_marshal",
    "assert_type_marshal_func",
    "assert_packet_marshal",
    "assert_packet_marshal_func",
]

def assert_type_marshal(type_cls, *values_and_data, ctx=None):
    r"""Asserts values marshal to and from expected data using a :class:`~.Type`.

    Parameters
    ----------
    type_cls : subclass of :class:`~.Type`
        The :class:`~.Type` to test.
    *values_and_data : pair of any and :class:`bytes`
        The values and data to test.
    ctx : :class:`~.TypeContext` or ``None``
        The context for the :class:`~.Type`.

    Examples
    --------
    >>> import pak
    >>> pak.test.assert_type_marshal(
    ...     pak.UInt8,
    ...
    ...     (1, b"\x01"),
    ...     (2, b"\x02"),
    ... )
    """

    for value, data in values_and_data:
        data_from_value = type_cls.pack(value, ctx=ctx)
        value_from_data = type_cls.unpack(data, ctx=ctx)

        assert data_from_value == data,  f"data_from_value={data_from_value}; data={data}; value={value}"
        assert value_from_data == value, f"value_from_data={value_from_data}; value={value}; data={data}"

def assert_type_marshal_func(*args, **kwargs):
    r"""Generates a function that calls :func:`assert_type_marshal`.

    This should be used only if you just need to compare values
    and raw data, and the values should be compared using equality.
    For anything else, you should create your own function, potentially
    one which uses :func:`assert_type_marshal`.

    Parameters
    ----------
    *args, **kwargs
        Forwarded to :func:`assert_type_marshal`.

    Examples
    --------
    >>> import pak
    >>> test_uint8 = pak.test.assert_type_marshal_func(
    ...     pak.UInt8,
    ...
    ...     (1, b"\x01"),
    ...     (2, b"\x02"),
    ... )
    >>> test_uint8()
    """

    return lambda: assert_type_marshal(*args, **kwargs)

def assert_packet_marshal(*packets_and_data, ctx=None):
    r"""Asserts :class:`~.Packet`\s marshal to and from expected data.

    Parameters
    ----------
    *packets_and_data : pair of :class:`~.Packet` and :class:`bytes`
        The :class:`~.Packet`\s and data to test.
    ctx : :class:`~.PacketContext`
        The context for the :class:`Packet`\s.

    Examples
    --------
    >>> import pak
    >>> class MyPacket(pak.Packet, id_type=pak.UInt8):
    ...     id = 1
    ...     field: pak.UInt8
    ...
    >>> pak.test.assert_packet_marshal(
    ...     (MyPacket(field=2), b"\x01\x02"),
    ...     (MyPacket(field=3), b"\x01\x03"),
    ... )
    """

    for packet, data in packets_and_data:
        data_file = util.file_object(data)

        id_from_packet = packet.id(ctx=ctx)
        id_from_data   = packet.unpack_id(data_file, ctx=ctx)

        assert id_from_packet == id_from_data, f"data={data}, packet={packet}"

        data_from_packet = packet.pack(ctx=ctx)
        packet_from_data = packet.unpack(data_file, ctx=ctx)

        assert data_from_packet == data,   f"data_from_packet={data_from_packet}; data={data}; packet={packet}"
        assert packet_from_data == packet, f"packet_from_data={packet_from_data}; packet={packet}; data={data}"

def assert_packet_marshal_func(*args, **kwargs):
    r"""Generates a function that calls :func:`assert_packet_marshal`.

    This should be used only if you just need to compare :class:`~.Packet`\s
    and raw data, and the :class:`~.Packet`\s should be compared using equality.
    For anything else, you should create your own function, potentially one which
    uses :func:`assert_packet_marshal`.

    Parameters
    ----------
    *args, **kwargs
        Forwarded to :func:`assert_packet_marshal`.

    Examples
    --------
    >>> import pak
    >>> class MyPacket(pak.Packet, id_type=pak.UInt8):
    ...     id = 1
    ...     field: pak.UInt8
    ...
    >>> test_my_packet = pak.test.assert_packet_marshal_func(
    ...     (MyPacket(field=2), b"\x01\x02"),
    ...     (MyPacket(field=3), b"\x01\x03"),
    ... )
    >>> test_my_packet()
    """

    return lambda: assert_packet_marshal(*args, **kwargs)
