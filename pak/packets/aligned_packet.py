"""Contains :class:`~.AlignedPacket`."""

from .. import util
from ..types.type import Type, TypeContext
from .packet import Packet

__all__ = [
    "AlignedPacket",
]

class AlignedPacket(Packet):
    """A :class:`~.Packet` which aligns its fields.

    .. seealso::

        :class:`~.AlignedCompound`

    The fields of an :class:`AlignedPacket` are aligned in the
    same way the fields of a struct would be in  C or C+, including
    the ending padding.

    The header of an :class:`AlignedPacket` is not taken into account
    when aligning fields.

    .. warning::

        An :class:`AlignedPacket` must have at least one field to be  used in full.
    """

    @classmethod
    @util.cache
    def alignment(cls, *, ctx=None):
        """Gets the total alignment of the :class:`AlignedPacket`.

        Parameters
        ----------
        ctx : :class:`~.PacketContext` or ``None``
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

        type_ctx = TypeContext(ctx=ctx)

        return max(t.alignment(ctx=type_ctx) for t in cls.field_types())

    @classmethod
    def _padding_lengths(cls, *, ctx):
        type_ctx = TypeContext(ctx=ctx)

        return Type.alignment_padding_lengths(
            *cls.field_types(),

            total_alignment = cls.alignment(ctx=ctx),
            ctx             = type_ctx,
        )

    @classmethod
    def unpack(cls, buf, *, ctx=None):
        """Overrides :meth:`.Packet.unpack` to handle alignment padding."""

        self = object.__new__(cls)

        buf = util.file_object(buf)

        type_ctx = self.type_ctx(ctx)
        for (field, field_type), padding_amount in zip(cls.enumerate_field_types(), cls._padding_lengths(ctx=ctx)):
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
        """Overrdies :meth:`.Packet.pack_without_header` to handle alignment padding."""

        type_ctx = self.type_ctx(ctx)

        return b"".join(
            field_type.pack(value, ctx=type_ctx) + b"\x00" * padding_amount

            for (field_type, value), padding_amount in zip(self.field_types_and_values(), self._padding_lengths(ctx=ctx))
        )

    def size(self, *, ctx=None):
        """Overrides :meth:`.Packet.size` to handle alignment padding."""

        return super().size(ctx=ctx) + sum(self._padding_lengths(ctx=ctx))
