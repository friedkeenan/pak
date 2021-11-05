"""Custom decorators."""

import functools
from collections.abc import Hashable

__all__ = [
    "cache",
]

def cache(func=None, *, force_hashable=True, max_size=None, **kwargs):
    """Custom decorator used to cache function results.

    Parameters
    ----------
    func : callable
        The function whose results should be cached.
    force_hashable : :class:`bool`
        Whether unhashable arguments should be allowed.

        If ``True``, then a :exc:`TypeError` is raised
        when unhashable arguments are passed.

        If ``False``, then if unhashable arguments are
        passed, caching is completely bypassed.
    max_size : :class:`int`
        The maximum size of the least-reused cache.

        If ``None``, then there is no limit, and cached
        values are never discarded.
    **kwargs
        Forwarded onto :func:`functools.lru_cache`.

    Returns
    -------
    callable
        The new function whose results will be cached.
    """

    if func is None:
        return lambda x: cache(x, force_hashable=force_hashable, max_size=max_size, **kwargs)

    internal_wrapper = functools.lru_cache(maxsize=max_size, **kwargs)(func)
    if force_hashable:
        return internal_wrapper

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not (
            all(isinstance(arg, Hashable) for arg in args) and
            all(isinstance(arg, Hashable) for arg in kwargs.values())
        ):
            return func(*args, **kwargs)

        return internal_wrapper(*args, **kwargs)

    return wrapper
