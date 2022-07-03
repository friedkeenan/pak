"""Miscellaneous utilities."""

__all__ = [
    "UniqueSentinel",
]

class UniqueSentinel:
    """An object with a unique identity.

    This is useful for e.g. default parameters that may have ``None`` as a valid value.

    Parameters
    ----------
    name : :class:`str` or ``None``
        The name of the :class:`UniqueSentinel`.

        If ``None``, then a default name is chosen.

        Returned when :func:`repr` is used on the object,
        mainly for the purpose of better docs.

    Examples
    --------
    >>> import pak
    >>> sentinel = pak.util.UniqueSentinel("SENTINEL")
    >>> sentinel
    SENTINEL
    >>> unnamed = pak.util.UniqueSentinel()
    >>> unnamed
    UniqueSentinel
    """

    def __init__(self, name=None):
        self.name = name

    def __repr__(self):
        if self.name is None:
            return "UniqueSentinel"

        return self.name
