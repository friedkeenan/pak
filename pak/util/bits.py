"""Utilities related to binary operations."""

__all__ = [
    "bit",
    "to_signed",
    "to_unsigned",
]

def bit(n):
    """Gets the number with the ``n``-th bit set.

    Parameters
    ----------
    n : :class:`int`
        The bit to set.

    Returns
    ------
    :class:`int`
        The number with the ``n``-th bit set.

    Examples
    --------
    >>> import pak
    >>> pak.util.bit(0)
    1
    >>> pak.util.bit(1)
    2
    >>> pak.util.bit(2)
    4
    """

    return (1 << n)

def to_signed(num, *, bits):
    """Converts a number to its signed counterpart.

    The two's complement representation of integers is used.

    See Also
    --------
    :func:`to_unsigned`

    Parameters
    ----------
    num : :class:`int`
        The number to convert.
    bits : :class:`int`
        The number of bits to use for the conversion.

    Returns
    -------
    :class:`int`
        The signed counterpart of ``num``.

    Examples
    --------
    >>> import pak
    >>> pak.util.to_signed(2**32 - 1, bits=32)
    -1
    >>> pak.util.to_signed(2**64 - 1, bits=64)
    -1
    >>> pak.util.to_signed(1, bits=32)
    1
    """

    if num > bit(bits - 1) - 1:
        num -= bit(bits)

    return num

def to_unsigned(num, *, bits):
    """Converts a number to its unsigned counterpart.

    The two's complement representation of integers is used.

    See Also
    --------
    :func:`to_signed`

    Parameters
    ----------
    num : :class:`int`
        The number to convert.
    bits : :class:`int`
        The number of bits to use for the conversion.

    Returns
    -------
    :class:`int`
        The unsigned counterpart of ``num``.

    Examples
    --------
    >>> import pak
    >>> pak.util.to_unsigned(-1, bits=32)
    4294967295
    >>> pak.util.to_unsigned(-1, bits=64)
    18446744073709551615
    >>> pak.util.to_unsigned(1, bits=32)
    1
    """

    if num < 0:
        num += bit(bits)

    return num
