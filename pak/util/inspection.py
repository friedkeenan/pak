"""Utilities for expanding upon the standard :mod:`inspect` module."""

import inspect

__all__ = [
    "subclasses",
    "arg_annotations",
]

def subclasses(*classes):
    """Gets the recursive subclasses of the arguments.

    Parameters
    ----------
    *classes : :class:`type`
        The types to get the subclasses of.

    Returns
    -------
    :class:`set`
        The recursive subclasses of the arguments.
    """

    recursive_subclasses = set()

    for cls in classes:
        direct_subclasses = cls.__subclasses__()

        recursive_subclasses |= set(direct_subclasses)
        recursive_subclasses |= subclasses(*direct_subclasses)

    return recursive_subclasses

def arg_annotations(func, *args, **kwargs):
    """Maps function arguments to their annotations.

    Parameters
    ----------
    func : :class:`function`
        The function to take annotations from.
    *args, **kwargs
        The arguments to map annotations to.

    Returns
    -------
    args_annotations : :class:`list`
        The annotations for ``*args``, of the form
        ``[(value, annotation)]``.
    kwargs_annotations : :class:`dict`
        The annotations for ``*args``, of the form
        ``{name: (value, annotation)}``.
    """

    parameters = inspect.signature(func).parameters

    args_annotations   = []
    kwargs_annotations = {}

    for i, (arg, param) in enumerate(zip(args, parameters.values())):
        if param.kind in (param.KEYWORD_ONLY, param.VAR_KEYWORD):
            raise TypeError("Too many positional arguments")

        if param.kind == param.VAR_POSITIONAL:
            args_annotations += [(x, param.annotation) for x in args[i:]]
            break

        args_annotations.append((arg, param.annotation))
    else:
        if len(args_annotations) != len(args):
            raise TypeError("Too many positional arguments")

    # Find the **kwargs parameter
    var_kwarg = None
    for param in parameters.values():
        if param.kind == param.VAR_KEYWORD:
            var_kwarg = param
            break

    for name, value in kwargs.items():
        param = parameters.get(name, var_kwarg)

        # If no corresponding parameter is found
        # and there's no var_kwarg
        if param is None:
            raise TypeError(f"Invalid keyword argument: {name}")

        if param.kind == param.POSITIONAL_ONLY:
            raise TypeError(f"Positional only argument: {name}")

        kwargs_annotations[name] = (value, param.annotation)

    return args_annotations, kwargs_annotations
