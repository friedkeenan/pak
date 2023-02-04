r""":class:`.Type`\s for combining :class:`.Type`\s."""

import collections
import dataclasses

from .. import util
from .type import Type

__all__ = [
    "Compound",
    "AlignedCompound",
]

class Compound(Type):
    r"""A :class:`.Type` comprised of other :class:`.Type`\s.

    The value type of a :class:`Compound` is a
    dataclass (from the :mod:`dataclasses` module).
    Setting the value to a :class:`tuple` (or other
    iterable) will convert the value to the value
    type of the :class:`Compound`.

    Parameters
    ----------
    name : :class:`str`
        The name of the new :class:`Compound`.
    **elems : typelike
        The name of the fields and their
        corresponding :class:`.Type`\s.

        The fields of a :class:`Compound` are
        contiguous with no spacing in between,
        and are ordered in the same order that
        ``**elems`` is passed in.
    """

    elems      = None
    value_type = None

    class _ValueBase:
        # This class is used to allow facilities
        # similar to 'namedtuple'.

        def __eq__(self, other):
            if isinstance(other, collections.abc.Mapping):
                return dataclasses.asdict(self) == other

            if isinstance(other, type(self)):
                other = dataclasses.astuple(other)

            return dataclasses.astuple(self) == other

        def __iter__(self):
            yield from dataclasses.astuple(self)

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if cls.elems is not None:
            cls.value_type = dataclasses.make_dataclass(cls.__qualname__, cls.elems.keys(), bases=(cls._ValueBase,), eq=False)

    @classmethod
    def types(cls):
        r"""Gets the :class:`.Type`\s of the fields of the :class:`Compound`.

        Parameters
        ----------
        iterable
            The :class:`.Type`\s of the fields of the :class:`Compound`.
        """

        return cls.elems.values()

    def __set__(self, instance, value):
        if isinstance(value, collections.abc.Mapping):
            value = self.value_type(**value)
        elif not isinstance(value, self.value_type):
            value = self.value_type(*value)

        super().__set__(instance, value)

    @classmethod
    def _size(cls, value, *, ctx):
        if value is cls.STATIC_SIZE:
            return sum(t.size(ctx=ctx) for t in cls.types())

        return sum(
            t.size(v, ctx=ctx) for v, t in zip(value, cls.types())
        )

    @classmethod
    def _default(cls, *, ctx):
        return cls.value_type(*(t.default(ctx=ctx) for t in cls.types()))

    @classmethod
    def _unpack(cls, buf, *, ctx):
        return cls.value_type(*(t.unpack(buf, ctx=ctx) for t in cls.types()))

    @classmethod
    def _pack(cls, value, *, ctx):
        if isinstance(value, collections.abc.Mapping):
            value = cls.value_type(**value)

        return b"".join(
            t.pack(v, ctx=ctx) for v, t in zip(value, cls.types())
        )

    @classmethod
    @Type.prepare_types
    def _call(cls, name, **elems: Type):
        return cls.make_type(name, elems=elems)

class AlignedCompound(Compound):
    r"""A :class:`Compound` which adds padding to keep its fields properly aligned.

    .. seealso::

        :class:`.AlignedPacket`

    The padding is the same as what you would get if you created a struct in C or C++,
    including the ending padding.

    .. warning::

        An :class:`AlignedCompound` must have at least one field to be used in full.
    """

    # NOTE: We currently decline to add an 'align_as' feature.
    #
    # I think there's too much to think about to justify adding
    # it presently. Maybe if there is demand for it in the
    # future it can be added.
    #
    # Additionally, the features that 'align_as' would give can
    # also be accomplished with manually creating 'Padding' fields,
    # albeit perhaps not as elegantly.
    #
    # Things to consider:
    # - Should an 'align_as' attribute be typelike, getting
    #   the alignment from the type?
    # - Should an 'align_as' attribute act like a DynamicValue?
    #   - If so, then should typelike alignment take priority?
    # - Should an 'align_as' attribute be able to be a list of
    #   typelikes and ints and DynamicValues?
    # - For 'AlignedPacket', should other AlignedPackets be able to
    #   be set to its 'align_as' attribute?
    # - Should individual fields be able to have 'align_as' applied to them?

    @classmethod
    def _padding_lengths(cls, *, ctx):
        return Type.alignment_padding_lengths(
            *cls.types(),

            total_alignment = cls.alignment(ctx=ctx),
            ctx             = ctx,
        )

    @classmethod
    def _size(cls, value, *, ctx):
        # Add the padding lengths and the static sizes of each type.
        return sum(cls._padding_lengths(ctx=ctx)) + sum(t.size(ctx=ctx) for t in cls.types())

    @classmethod
    def _alignment(cls, *, ctx):
        # Return the strictest alignment.
        return max(t.alignment(ctx=ctx) for t in cls.types())

    @classmethod
    def _unpack(cls, buf, *, ctx):
        values = []
        for t, padding_amount in zip(cls.types(), cls._padding_lengths(ctx=ctx)):
            values.append(t.unpack(buf, ctx=ctx))
            buf.read(padding_amount)

        return cls.value_type(*values)

    @classmethod
    def _pack(cls, value, *, ctx):
        return b"".join(
            t.pack(v, ctx=ctx) + b"\x00" * padding_amount

            for v, t, padding_amount in zip(value, cls.types(), cls._padding_lengths(ctx=ctx))
        )
