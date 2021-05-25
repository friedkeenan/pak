"""Custom decorators."""

import functools
from collections.abc import Hashable

def cache(func):
    """Custom decorator used to cache function results.

    If unhashable types are passed to the function,
    then no caching occurs and the function runs
    as normal.

    Parameters
    ----------
    func : callable
        The function whose results should be cached.

    Returns
    -------
    callable
        The new function whose results will be cached.
    """

    internal_wrapper = functools.lru_cache(maxsize=None)(func)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not (
            all(isinstance(arg, Hashable) for arg in args) and
            all(isinstance(arg, Hashable) for arg in kwargs.values())
        ):
            return internal_wrapper.__wrapped__(*args, **kwargs)

        return internal_wrapper(*args, **kwargs)

    return wrapper
