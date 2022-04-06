r""":class:`~.Type`\s for manipulating default values."""

from .type import Type

__all__ = [
    "Defaulted",
]

class Defaulted(Type):
    """A :class:`~.Type` with a custom default value.

    The resulting :class:`~.Type` inherits from
    ``elem_type`` and :class:`Defaulted`, in that order.

    Parameters
    ----------
    elem_type : typelike
        The :class:`~.Type` to modify the default of.
    default
        The new default value.

    Examples
    --------
    >>> import pak
    >>> DefaultedInt8 = pak.Defaulted(pak.Int8, 1)
    >>> DefaultedInt8.default()
    1
    """

    @classmethod
    @Type.prepare_types
    def _call(cls, elem_type: Type, default):
        return cls.make_type(
            f"{cls.__qualname__}{elem_type.__qualname__}",
            (elem_type, cls),

            _default = default,
        )
