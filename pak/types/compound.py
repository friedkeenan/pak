r""":class:`~.Type`\s for combining :class:`~.Type`\s."""

from collections import namedtuple

from .type import Type

__all__ = [
    "Compound",
]

class Compound(Type):
    r"""A :class:`~.Type` comprised of other :class:`~.Type`\s.

    The value type of a :class:`Compound` is a
    :func:`collections.namedtuple`. Setting the
    value to a :class:`tuple` (or other iterable)
    will convert the value to the value type of
    the :class:`Compound`.

    Parameters
    ----------
    name : :class:`str`
        The name of the new :class:`Compound`.
    **elems : typelike
        The name of the fields and their
        corresponding :class:`~.Type`\s.

        The fields of a :class:`Compound` are
        contiguous with no spacing in between,
        and are ordered in the same order that
        ``**elems`` is passed in.
    """

    elems      = None
    value_type = None

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        cls.value_type = namedtuple(cls.__qualname__, cls.elems.keys())

    @classmethod
    def types(cls):
        r"""Gets the :class:`~.Type`\s of the fields of the :class:`Compound`.

        Parameters
        ----------
        iterable
            The :class:`~.Type`\s of the fields of the :class:`Compound`.
        """

        return cls.elems.values()

    def __set__(self, instance, value):
        if not isinstance(value, self.value_type):
            value = self.value_type(*value)

        super().__set__(instance, value)

    @classmethod
    def _default(cls, *, ctx):
        return cls.value_type(*(t.default(ctx=ctx) for t in cls.types()))

    @classmethod
    def _unpack(cls, buf, *, ctx):
        return cls.value_type(*(t.unpack(buf, ctx=ctx) for t in cls.types()))

    @classmethod
    def _pack(cls, value, *, ctx):
        return b"".join(
            t.pack(v, ctx=ctx) for v, t in zip(value, cls.types())
        )

    @classmethod
    @Type.prepare_types
    def _call(cls, name, **elems: Type):
        return cls.make_type(name, elems=elems)
