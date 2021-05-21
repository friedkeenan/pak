"""Utilities for checking object interfaces."""

import io

__all__ = [
    "is_iterable",
    "file_object",
]

def is_iterable(obj):
    """Checks if an object is iterable.

    Parameters
    ----------
    obj
        The object to check. ``obj`` is iterable if it can
        be used in the following expression::

            for x in obj:
                pass

    Returns
    -------
    :class:`bool`
        Whether ``obj`` is iterable.
    """

    try:
        iter(obj)
    except TypeError:
        return False

    return True

def file_object(obj):
    """Converts an object to a file object.

    Parameters
    ----------
    obj : file object or :class:`bytes` or :class:`bytearray`
        The object to convert.

    Returns
    -------
    file object
        The corresponding file object.
    """

    if isinstance(obj, (bytes, bytearray)):
        return io.BytesIO(obj)

    return obj
