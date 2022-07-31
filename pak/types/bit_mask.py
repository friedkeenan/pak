r""":class:`.Type`\s for bitmasks."""

from collections import namedtuple

from .. import util
from .type import Type

__all__ = [
    "BitMask",
]

class BitMask(Type):
    """A :class:`.Type` for bitmasks.

    The value type of a :class:`BitMask` is a
    :func:`collections.namedtuple`. Setting
    the value to a :class:`tuple` (or other
    iterable) will convert the value to the
    value type of the :class:`BitMask`.

    Parameters
    ----------
    name : :class:`str`
        The name of the new :class:`BitMask`.
    elem_type : typelike
        The underlying integer type.
    **masks
        The name of the fields and their corresponding
        bits. They are ordered in the same order that
        ``**masks`` is passed in.

        If the value is a single :class:`int`, then that
        field is given a :class:`bool` value, mapping to that
        bit.

        Otherwise the value should be a sequence of two
        ints representing the range of bits that field
        occupies. The bit range, as with Python's
        :class:`range`, is [start, end).
    """

    elem_type  = None
    masks      = None
    value_type = None

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        cls.value_type = namedtuple(
            cls.__qualname__,
            cls.masks.keys(),

            defaults = [
                False if isinstance(bits, int) else 0

                for bits in cls.masks.values()
            ]
        )

    def __set__(self, instance, value):
        if not isinstance(value, self.value_type):
            value = self.value_type(*value)

        super().__set__(instance, value)

    @classmethod
    def _size(cls, value, *, ctx):
        return cls.elem_type.size(ctx=ctx)

    @classmethod
    def _default(cls, *, ctx):
        return cls.value_type()

    @classmethod
    def _unpack(cls, buf, *, ctx):
        int_value = cls.elem_type.unpack(buf, ctx=ctx)

        elems = []
        for bits in cls.masks.values():
            if isinstance(bits, int):
                value = int_value & util.bit(bits) != 0
            else:
                bit_range = util.bit(bits[1] - bits[0]) - 1

                value = (int_value & (bit_range << bits[0])) >> bits[0]

            elems.append(value)

        return cls.value_type(*elems)

    @classmethod
    def _pack(cls, value, *, ctx):
        int_value = 0

        for bits, elem in zip(cls.masks.values(), value):
            if isinstance(bits, int):
                if elem:
                    int_value |= util.bit(bits)
                else:
                    int_value &= ~util.bit(bits)
            else:
                bit_range = util.bit(bits[1] - bits[0]) - 1

                if elem != (elem & bit_range):
                    raise ValueError(f"Value {elem} too wide for range {bits}")

                # Clear the old bits and shift the
                # new ones into place.
                int_value &= ~(bit_range << bits[0])
                int_value |= (elem << bits[0])

        return cls.elem_type.pack(int_value, ctx=ctx)

    @classmethod
    @Type.prepare_types
    def _call(cls, name, elem_type: Type, **masks):
        return cls.make_type(
            name,

            elem_type = elem_type,
            masks     = masks,
        )
