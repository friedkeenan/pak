"""Custom decorators."""

import functools
from collections.abc import Hashable

__all__ = [
    "cache",
    "class_or_instance_method",
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

class class_or_instance_method:
    """A decorator to call either a class method or an instance method.

    The :attr:`__doc__` attribute is set to the :attr:`__doc__` attribute
    of the associated class method.

    This, similarly to :class:`classmethod`, propagates other descriptors
    as well, allowing combinations of :class:`class_or_instance_method` with
    :class:`property` for example.

    Parameters
    ----------
    class_method : function
        The function for the class method.
    instance_method : function or ``None``
        The function for the instance method.

    Examples
    --------
    >>> import pak
    >>> class MyClass:
    ...     @pak.util.class_or_instance_method
    ...     def method(cls):
    ...         return "class"
    ...
    ...     @method.instance_method
    ...     def method(self):
    ...         return "instance"
    ...
    >>> MyClass.method()
    'class'
    >>> MyClass().method()
    'instance'
    """

    def __init__(self, class_method, instance_method=None):
        self._class_method    = class_method
        self._instance_method = instance_method

        self.__doc__ = class_method.__doc__

    def instance_method(self, instance_method):
        """A decorator that sets the instance method.

        .. warning::

            The instance method **must** be set, otherwise
            an error will be raised.

        Parameters
        ----------
        instance_method : function
            The function for the instance method.

        Returns
        -------
        :class:`class_or_instance_method`
            The descriptor with the newly set instance method.
        """

        return type(self)(self._class_method, instance_method)

    def class_method(self, class_method):
        """A decorator that sets the class method.

        Parameters
        ----------
        class_method : function
            The function for the class method.

        Returns
        -------
        :class:`class_or_instance_method`
            The descriptor with the newly set class method.
        """

        return type(self)(class_method, self._instance_method)

    def __set_name__(self, owner, name):
        if self._instance_method is None:
            raise TypeError(f"{type(self).__qualname__} '{owner.__qualname__}.{name}' must have an instance method")

    def __get__(self, instance, owner=None):
        # 'classmethod' in fact propagates the '__get__' call instead of
        # just returning a bound method. This allows users to create
        # "class properties" by combining 'classmethod' and 'property'.
        # We support the same here.

        if instance is None:
            return self._class_method.__get__(owner, owner)

        return self._instance_method.__get__(instance, owner)
