r""":class:`.Packet`\s which align their fields."""

from .. import util
from ..types.type import Type

from .packet import Packet

__all__ = [
    "AlignedPacket",
    "AlignedHeader",
]

class AlignedPacket(Packet):
    """A :class:`.Packet` which aligns its fields.

    The fields of an :class:`AlignedPacket` are aligned in the
    same way the fields of a struct would be in  C or C++, including
    the ending padding.

    The header of an :class:`AlignedPacket` is not taken into account
    when aligning fields.

    .. warning::

        An :class:`AlignedPacket` must have at least one field to be used in full.
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
    # - Should other AlignedPackets be able to be set to its
    #   'align_as' attribute?
    # - Should individual fields be able to have 'align_as' applied to them?

    @classmethod
    @util.cache
    def alignment(cls, *, ctx=None):
        """Gets the total alignment of the :class:`AlignedPacket`.

        Parameters
        ----------
        ctx : :class:`.Packet.Context` or ``None``
            The context for the :class:`AlignedPacket`.

        Returns
        -------
        :class:`int`
            The total alignment of the :class:`AlignedPacket`.

        Examples
        --------
        >>> import pak
        >>> class MyPacket(pak.AlignedPacket):
        ...     first: pak.Int16
        ...     second: pak.Int32
        ...     third: pak.Int8
        ...
        >>> MyPacket.alignment()
        4
        """

        if ctx is None:
            ctx = cls.Context()

        type_ctx = Type.Context(ctx=ctx)

        return max(t.alignment(ctx=type_ctx) for t in cls.field_types())

    @classmethod
    def _padding_lengths(cls, *, type_ctx):
        return Type.alignment_padding_lengths(
            *cls.field_types(),

            total_alignment = cls.alignment(ctx=type_ctx.packet_ctx),
            ctx             = type_ctx,
        )

    @classmethod
    def unpack(cls, buf, *, ctx=None):
        """Overrides :meth:`.Packet.unpack` to handle alignment padding."""

        self = object.__new__(cls)

        buf = util.file_object(buf)

        type_ctx = self.type_ctx(ctx)
        for (field, field_type), padding_amount in zip(cls.enumerate_field_types(), cls._padding_lengths(type_ctx=type_ctx)):
            value = field_type.unpack(buf, ctx=type_ctx)
            buf.read(padding_amount)

            try:
                setattr(self, field, value)

            except AttributeError:
                # If trying to set an unpacked value fails
                # (like if the attribute is read-only)
                # then just move on.
                pass

        return self

    def pack_without_header(self, *, ctx=None):
        """Overrides :meth:`.Packet.pack_without_header` to handle alignment padding."""

        type_ctx = self.type_ctx(ctx)

        return b"".join(
            field_type.pack(value, ctx=type_ctx) + b"\x00" * padding_amount

            for (field_type, value), padding_amount in zip(self.field_types_and_values(), self._padding_lengths(type_ctx=type_ctx))
        )

    @util.class_or_instance_method
    def size(cls, *, ctx=None):
        """Overrides :meth:`.Packet.size` to handle alignment padding."""

        if ctx is None:
            ctx = cls.Context()

        type_ctx = Type.Context(ctx=ctx)

        return super().size(ctx=ctx) + sum(cls._padding_lengths(type_ctx=type_ctx))

    @size.instance_method
    def size(self, *, ctx=None):
        type_ctx = self.type_ctx(ctx)

        return super().size(ctx=ctx) + sum(self._padding_lengths(type_ctx=type_ctx))

class AlignedHeader(Packet.Header, AlignedPacket):
    r"""A :class:`.Packet.Header` which aligns its fields.

    This is not the default header of :class:`AlignedPacket`
    since :class:`AlignedPacket`\s may often have headers which
    do not align their fields, nor even have any header at all.
    Additionally, there are unaligned :class:`.Packet`\s which
    may have headers which align their fields.

    This class is nevertheless still provided however as the
    double inheritance required may be tricky to get right.

    .. note::

        There is no alignment performed between the header
        and the :class:`.Packet` proper.

    Examples
    --------
    >>> import pak
    >>> class MyPacket(pak.Packet):
    ...     id = 1
    ...     field: pak.UInt64
    ...     class Header(pak.AlignedHeader):
    ...         id:   pak.UInt8
    ...         size: pak.UInt16
    ...
    >>> MyPacket.Header.alignment()
    2
    >>> # The '\xAA' byte represents alignment padding.
    >>> MyPacket.Header.unpack(b"\x01\xAA\x08\x00")
    MyPacket.Header(id=1, size=8)
    >>> MyPacket(field=2).pack()
    b'\x01\x00\x08\x00\x02\x00\x00\x00\x00\x00\x00\x00'
    """
