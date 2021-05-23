"""Custom decorators."""

import functools

# TODO: Remove when 3.8 support is dropped.
def cache(func):
    """Custom-ish decorator used to cache function results.

    Only exists because :func:`functools.cache` was only added
    in Python 3.9. Our implementation is the same as the standard
    library's.

    Parameters
    ----------
    func : callable
        The function whose results should be cached.

    Returns
    -------
    :class:`function`
        The new function whose results will be cached.
    """

    return functools.lru_cache(maxsize=None)(func)
