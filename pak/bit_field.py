"""Contains :class:`.BitField`."""

import inspect

from . import util

from .types.type import Type

__all__ = [
    "BitField",
]

class _BitFieldType(Type):
    bitfield_cls = None
    underlying   = None

    @classmethod
    def _size(cls, value, *, ctx):
        if value is cls.STATIC_SIZE:
            return cls.underlying.size(ctx=ctx)

        return cls.underlying.size(value.pack_to_int(), ctx=ctx)

    @classmethod
    def _alignment(cls, *, ctx):
        return cls.underlying.alignment(ctx=ctx)

    @classmethod
    def _default(cls, *, ctx):
        return cls.bitfield_cls()

    @classmethod
    def _unpack(cls, buf, *, ctx):
        return cls.bitfield_cls.unpack_from_int(cls.underlying.unpack(buf, ctx=ctx))

    @classmethod
    async def _unpack_async(cls, reader, *, ctx):
        return cls.bitfield_cls.unpack_from_int(await cls.underlying.unpack_async(reader, ctx=ctx))

    @classmethod
    def _pack(cls, value, *, ctx):
        return cls.underlying.pack(value.pack_to_int(), ctx=ctx)

    @classmethod
    def _call(cls, name, bitfield_cls, underlying):
        return cls.make_type(
            name,

            bitfield_cls = bitfield_cls,
            underlying   = underlying,
        )


class BitField:
    r"""A collection of data packed into specific bits of an underlying integer.

    A definition of a :class:`BitField` looks like this::

        class MyBitField(pak.BitField):
            boolean_field: 1
            integer_field: 2
            other_field:   2

    ``MyBitField`` inherits from :class:`BitField`, and its annotations
    specify the bit widths of each of its fields, starting at the least
    significant bit.

    Fields which have a bit width of ``1`` will have a :class:`bool`
    value, corresponding to whether the appropriate bit is set or unset.

    Fields which have a bit width larger than ``1`` will have an :class:`int`
    value.

    If a field is specified to have a bit width of ``0``, then a
    :exc:`TypeError` is raised.

    Parameters
    ----------
    **fields
        The names and corresponding values of the
        fields of the :class:`BitField`.

    Raises
    ------
    :exc:`TypeError`
        If there are any superfluous keyword arguments.
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        for base in cls.mro()[1:]:
            if base is BitField:
                continue

            if issubclass(base, BitField):
                raise TypeError("BitFields may not be inherited from")

        cls._fields = inspect.get_annotations(cls)

        if 0 in cls._fields.values():
            raise TypeError("A BitField may not have a field of width '0'")

    @classmethod
    @Type.prepare_types
    def Type(cls, underlying: Type):
        """Makes a :class:`.Type` which works with :class:`BitField` values.

        Parameters
        ----------
        underlying : typelike
            The underlying integer :class:`.Type` which
            works with the packed integer value.

        Returns
        -------
        subclass of :class:`.Type`
            The corresponding :class:`.Type`.
        """

        return _BitFieldType(f"{cls.__qualname__}.Type({underlying.__qualname__})", cls, underlying)

    def __init__(self, **fields):
        for attr, bit_width in self._fields.items():
            if attr in fields:
                setattr(self, attr, fields.pop(attr))

                continue

            else:
                setattr(self, attr, False if bit_width == 1 else 0)

        if len(fields) != 0:
            raise TypeError(f"Unexpected keyword arguments for '{type(self).__qualname__}': {fields}")

    @classmethod
    def unpack_from_int(cls, value):
        """Unpacks a :class:`BitField` from an :class:`int`.


        Parameters
        ----------
        value : :class:`int`
            The integer value containing the packed data.

        Returns
        -------
        :class:`BitField`
            The corresponding :class:`BitField`.
        """

        self = object.__new__(cls)

        start_bit = 0
        for field, bit_width in cls._fields.items():
            if bit_width == 1:
                setattr(self, field, value & util.bit(start_bit) != 0)
            else:
                bit_range = util.bit(bit_width) - 1

                setattr(self, field, (value >> start_bit) & bit_range)

            start_bit += bit_width

        return self

    def pack_to_int(self):
        """Packs a :class:`BitField` into an :class:`int`.

        Returns
        -------
        :class:`int`
            The corresponding integer value containing the packed data.

        Raises
        ------
        :exc:`ValueError`
            If a field's value is too wide for its corresponding width.
        """

        result = 0

        start_bit = 0
        for field, bit_width in self._fields.items():
            field_value = getattr(self, field)

            if bit_width == 1:
                if field_value:
                    result |= util.bit(start_bit)
                else:
                    result &= ~util.bit(start_bit)

            else:
                bit_range = util.bit(bit_width) - 1

                if field_value != (field_value & bit_range):
                    raise ValueError(f"Value '{field_value}' is too wide for width '{bit_width}' of field '{field}'")

                # Clear the old bits and shift
                # the new ones into place.
                result &= ~(bit_range << start_bit)
                result |= (field_value << start_bit)

            start_bit += bit_width

        return result

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented

        return all(
            getattr(self, field) == getattr(other, field)

            for field in self._fields.keys()
        )

    def __repr__(self):
        return (
            f"{type(self).__qualname__}("

            +

            ", ".join(
                f'{attr}={repr(getattr(self, attr))}'
                for attr in self._fields.keys()
            )

            +

            ")"
        )
