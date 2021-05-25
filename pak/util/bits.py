"""Utilities related to binary operations."""

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
