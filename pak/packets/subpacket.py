r""":class:`.Packet`\s which are contained in other :class:`.Packet`\s."""

from .. import util

from ..types.type import Type

from .packet         import Packet, GenericPacket
from .aligned_packet import AlignedPacket

__all__ = [
    "SubPacket",
    "AlignedSubPacket",
]

# NOTE: We use this metaclass so that
# we can register it as a typelike, since
# the typelike machinery expects *instances*
# of the types registered with it, not subclasses.
#
# We could have some sort of 'register_subclasses_as_typelike'
# function to append a different qualification for
# something to be typelike, but I don't think there's
# a genuine use case for such a thing outside of
# this one situation, and so we have settled for
# the use of a metaclass.
class _SubPacketMeta(type):
    pass

class SubPacket(Packet, metaclass=_SubPacketMeta):
    r"""A :class:`.Packet` contained within another :class:`.Packet`.


    A frequent occurrence in many protocols are :class:`.Packet`\s
    which have certain structures within them which associate data
    together. This could be just a conceptual distincition, or it
    could be a more practical distinction. These structures can be
    thought of as "sub-packets".

    For instance, if we had a packet which had a variable amount of
    pairs of names of players and their levels, represented with a leading
    :class:`.UInt16` which reports how many pairs there are, and then
    a :class:`.TerminatedString` for the name and a :class:`.UInt8`
    for the level, we could define such a :class:`SubPacket`:

    .. testcode::

        import pak

        class PlayerNameAndLevel(pak.SubPacket):
            name:  pak.TerminatedString
            level: pak.UInt8

    We could then use it in a normal :class:`.Packet` like a :class:`.Type`:

    .. testcode::

        class PlayerInfoPacket(pak.Packet):
            players: PlayerNameAndLevel[pak.UInt16]

    And we can then use it all like so:

    .. testcode::

        packet = PlayerInfoPacket(players=[
            PlayerNameAndLevel(name="Bob",   level=1),
            PlayerNameAndLevel(name="Alice", level=2),
        ])

        assert packet.pack() == (
            b"\x02\x00" + b"Bob\x00\x01" + b"Alice\x00\x02"
        )

    .. note::

        :class:`SubPacket`\s (or rather, its subclasses) are typelike,
        enabling their use like any other :class:`.Type`.

        Additionally, the terse array syntax of ``ElemType[size]`` works
        with :class:`SubPacket`\s as well.

    And because :class:`SubPacket`\s are still :class:`.Packet`\s, they
    can leverage a bit of that functionality, notably with their header.

    .. note::

        :class:`SubPacket`\s cannot define their own :class:`.Packet.Context`,
        as they should receive and use the context of their super :class:`.Packet`.

    :class:`SubPacket` headers may only have a ``size`` field and/or an
    ``id`` field.  When a :class:`SubPacket` header contains a ``size``
    field, then that many bytes will be read from the buffer supplied to
    the super :class:`.Packet` and used to unpack the :class:`SubPacket`:

    .. testcode::

        import pak

        class SizedSubPacket(pak.SubPacket):
            class Header(pak.SubPacket.Header):
                size: pak.UInt8

            data: pak.RawByte[None]

        class MyPacket(pak.Packet):
            sized: SizedSubPacket
            rest:  pak.RawByte[None]

        assert MyPacket.unpack(
            # The 'rest' data should not be consumed by the 'sized' field.
            b"\x0Asized data" + b"rest"
        ) == MyPacket(
            sized = SizedSubPacket(data=b"sized data"),
            rest  = b"rest",
        )

    When a :class:`SubPacket` header contains an ``id`` field, then a subclass
    of the :class:`SubPacket` is searched for using :meth:`.Packet.subclass_with_id`,
    and then used to marshal the data:

    .. testcode::

        import pak

        class IDSubPacket(pak.SubPacket):
            class Header(pak.SubPacket.Header):
                id: pak.UInt8

        class NumberData(IDSubPacket):
            id = 1

            number: pak.UInt16

        class ArrayData(IDSubPacket):
            id = 2

            array: pak.UInt8[2]

        class DataPacket(pak.Packet):
            data: IDSubPacket

        assert DataPacket.unpack(
            b"\x01" + b"\x02\x00"
        ) == DataPacket(
            data = NumberData(number=2),
        )

        assert DataPacket.unpack(
            b"\x02" + b"\x00\x01"
        ) == DataPacket(
            data = ArrayData(array=[0, 1]),
        )

    When an unknown ID is encountered, then :meth:`_subclass_for_unknown_id`
    is called, allowing customization for different needs.
    """

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if issubclass(cls, AlignedPacket) and cls.Header is not AlignedPacket.Header:
            # NOTE: I don't think it makes sense for an aligned
            # subpacket to have a header, since that would imply
            # the capability of a dynamic size. If a user really
            # wants some sort of aligned subpacket, then they can
            # define their own custom type.
            raise TypeError(f"'{cls.__qualname__}' may not define its own header because it as an 'AlignedPacket'")

        for name in cls.Header.field_names():
            if name not in ("id", "size"):
                raise TypeError(f"The header for '{cls.__qualname__}' may not have the field '{name}', only 'id' or 'size'")

        if cls.Context is not Packet.Context:
            raise TypeError(f"'{cls.__qualname__}' may have no context of its own")

    @classmethod
    def _subclass_for_unknown_id(cls, id, *, ctx):
        """Gets the subclass for the :class:`SubPacket` when an unknown ID is encountered.

        This method is overridable in order to customize the relevant behavior.
        For instance, a subclass from :meth:`.Packet.GenericWithID` or
        :meth:`.Packet.EmptyWithID` could be returned.

        By default, a :exc:`ValueError` is raised upon encountering an unknown ID.

        Parameters
        ----------
        id
            The unknown ID.
        ctx : :class:`.Packet.Context`
            The context for the :class:`SubPacket`.

        Returns
        -------
        Subclass of :class:`SubPacket`
            The subclass of the :class:`SubPacket`.
        """

        raise ValueError(f"Unknown ID encountered for '{cls.__qualname__}': {repr(id)}")

    @classmethod
    def __class_getitem__(cls, index):
        # Allow terse array syntax with SubPackets.

        return _SubPacketType(cls)[index]

class AlignedSubPacket(SubPacket, AlignedPacket):
    """A :class:`SubPacket` which aligns its fields.

    When converted to a :class:`.Type`, the alignment
    of the :class:`AlignedSubPacket` will be propagated
    appropriately, namely to its super :class:`.Packet`.

    .. note::

        If an :class:`AlignedSubPacket` defines its own
        header, then a :exc:`TypeError` is raised.
    """

class _SubPacketType(Type):
    subpacket_cls = None

    @classmethod
    def _size(cls, value, *, ctx):
        if value is cls.STATIC_SIZE:
            # If there is an ID or size in the header, then we
            # can't statically know the size of the packet.
            if len(cls.subpacket_cls.Header.field_names()) > 0:
                return None

            return cls.subpacket_cls.Header.size(ctx=ctx.packet_ctx) + cls.subpacket_cls.size(ctx=ctx.packet_ctx)

        return value.header(ctx=ctx.packet_ctx)._size_impl(ctx=ctx.packet_ctx) + value.size(ctx=ctx.packet_ctx)

    @classmethod
    def _alignment(cls, *, ctx):
        if not issubclass(cls.subpacket_cls, AlignedPacket):
            return None

        return cls.subpacket_cls.alignment(ctx=ctx.packet_ctx)

    @classmethod
    def _default(cls, *, ctx):
        if cls.subpacket_cls.Header.has_field("id"):
            raise TypeError(f"Cannot get default for '{cls.subpacket_cls.__qualname__}' because its header includes an ID")

        return cls.subpacket_cls(ctx=ctx.packet_ctx)

    @classmethod
    def _unpack(cls, buf, *, ctx):
        header = cls.subpacket_cls.Header.unpack(buf, ctx=ctx.packet_ctx)

        if header.has_field("size"):
            packet_buf = buf.read(header.size)
        else:
            packet_buf = buf

        if header.has_field("id"):
            packet_cls = cls.subpacket_cls.subclass_with_id(header.id, ctx=ctx.packet_ctx)
            if packet_cls is None:
                packet_cls = cls.subpacket_cls._subclass_for_unknown_id(header.id, ctx=ctx.packet_ctx)
        else:
            packet_cls = cls.subpacket_cls

        return packet_cls.unpack(packet_buf, ctx=ctx.packet_ctx)

    @classmethod
    def _pack(cls, value, *, ctx):
        return value.pack(ctx=ctx.packet_ctx)

    @classmethod
    def _call(cls, subpacket_cls):
        return cls.make_type(
            f"{cls.__qualname__}({subpacket_cls.__qualname__})",

            subpacket_cls = subpacket_cls,
        )

Type.register_typelike(_SubPacketMeta, _SubPacketType)
