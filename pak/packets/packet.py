r"""Generic code for :class:`~.Packet`\s."""

# This module isn't split up currently because it has
# so few members, but in the event it gets too large,
# it should be split up.

import inspect

from .. import util
from ..dyn_value import DynamicValue
from ..types.type import Type
from ..types.misc import RawByte, EmptyType

__all__ = [
    "ReservedFieldError",
    "DuplicateFieldError",
    "Packet",
    "GenericPacket",
]

class ReservedFieldError(Exception):
    """An error indicating a field was defined with a reserved name.

    See :attr:`Packet.RESERVED_FIELDS` for more information.

    Parameters
    ----------
    packet_cls : subclass of :class:`Packet`
        The :class:`Packet` which used a reserved field name.
    field : :class:`str`
        The name of the offending field.
    """

    def __init__(self, packet_cls, field):
        super().__init__(f"Definition of a field with a reserved name '{field}' in packet '{packet_cls.__qualname__}'")

class DuplicateFieldError(Exception):
    """An error indicating a field was defined twice.

    Raised when declaring a field already declared in a parent :class:`Packet`.

    Parameters
    ----------
    packet_cls : subclass of :class:`Packet`
        The :class:`Packet` which duplicated a field.
    field : :class:`str`
        The name of the field which was duplicated.
    """

    def __init__(self, packet_cls, field):
        super().__init__(f"Duplicate definition of '{field}' in packet '{packet_cls.__qualname__}'")

class Packet:
    r"""A collection of values that can be marshaled to and from
    raw data using :class:`~.Type`\s.

    The difference between a :class:`Packet` and a :class:`~.Type`
    is that :class:`~.Type`\s only define how to marshal values
    to and from raw data, while :class:`Packet`\s actually *contain*
    values themselves.

    To unpack a :class:`Packet` from raw data, you should use
    the :meth:`unpack` method instead of the constructor.

    Parameters
    ----------
    ctx : :class:`Packet.Context`
        The context for the :class:`Packet`.
    **fields
        The names and corresponding values of the fields
        of the :class:`Packet`.

    Raises
    ------
    :exc:`TypeError`
        If there are any superfluous keyword arguments.

    Examples
    --------
    Basic functionality::

        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     attr1: pak.Int8
        ...     attr2: pak.Int16
        ...
        >>> p = MyPacket()
        >>> p
        MyPacket(attr1=0, attr2=0)
        >>> p.pack()
        b'\x00\x00\x00'
        >>> p = MyPacket(attr1=1, attr2=2)
        >>> p.pack()
        b'\x01\x02\x00'
        >>> MyPacket.unpack(b"\xff\x00\x80")
        MyPacket(attr1=-1, attr2=-32768)

    Additionally your attributes can be properties::

        >>> class MyPacket(pak.Packet):
        ...     prop: pak.Int8
        ...     @property
        ...     def prop(self):
        ...         return self._prop
        ...     @prop.setter
        ...     def prop(self, value):
        ...         self._prop = value + 1
        ...
        >>> p = MyPacket()
        >>> p # Int8's default is 0, plus 1 is 1
        MyPacket(prop=1)
        >>> p.prop = 2
        >>> p
        MyPacket(prop=3)
        >>> p.pack()
        b'\x03'

    If an attribute is read only, it will only raise an error
    if you explicitly try to set it, i.e. you specify the value
    for it in the constructor.
    """

    class _ContextMeta(type):
        # A metaclass to ensure Packet.Context subclasses are properly hashable.
        #
        # This metaclass is unfortunately needed since for whatever reason checking
        # for 'cls.__hash__ is super().__hash__' in '__init_subclass__' does not
        # work for this. Additionally this allows users to do something like
        # '__hash__ = Packet.Context.__hash__' to give an implementation and have it work.

        def __new__(cls, name, bases, namespace):
            if namespace.get("__hash__") is None:
                raise TypeError(f"'{namespace['__qualname__']}' must provide a '__hash__' implementation")

            return super().__new__(cls, name, bases, namespace)

    class Context(metaclass=_ContextMeta):
        r"""The context for a :class:`Packet`.

        :class:`Packet.Context`\s are used to pass arbitrary data
        to :class:`Packet` operations, typically just being wrapped
        in a :class:`.Type.Context` and sent off to :class:`~.Type`
        operations, such as unpacking and packing.

        You should customize this class to suit your own purposes,
        like so::

            >>> import pak
            >>> class MyPacket(pak.Packet):
            ...     class Context(pak.Packet.Context):
            ...         def __init__(self):
            ...             self.info = ...
            ...             super().__init__()
            ...
            ...         def __hash__(self):
            ...             return hash(self.info)
            ...

        When no :class:`Packet.Context` is provided to :class:`Packet`
        operations that may accept one, then your subclass is attempted
        to be defaultl constructed and used instead.

        Warnings
        --------
        Subclasses **must** be properly hashable. Accordingly, this
        means that subclasses should also be immutable. Therefore,
        the constructor of :class:`Packet.Context` sets the constructed
        object to be immutable.

        If a subclass of :class:`Packet.Context` does not provide its
        own ``__hash__`` implementation, then a :exc:`TypeError` is raised.
        """

        def __init__(self):
            self._mutable_flag = True

        def __setattr__(self, attr, value):
            if hasattr(self, "_mutable_flag"):
                raise TypeError(f"'{type(self).__qualname__}' is immutable")

            super().__setattr__(attr, value)

        def __hash__(self):
            # A default 'Packet.Context' has no unique information.
            return hash(tuple())

    # The fields dictionary for 'Packet'.
    #
    # Since 'Packet' has no annotations, and has no parent to fall back on
    # for its fields, we define it here.
    _fields = {}

    # Will be replaced after 'Packet' is defined.
    class Header:
        pass

    RESERVED_FIELDS = [
        "ctx",
    ]

    @classmethod
    def id(cls, *, ctx=None):
        r"""Gets the ID of the :class:`Packet`.

        Lots of packet protocols specify :class:`Packet`\s with
        an ID to determine what type of :class:`Packet` should
        be read. Unless overridden, :class:`Packet` has no
        meaningful ID.

        If the :attr:`id` attribute of a subclass is enrolled
        in the :class:`~.DynamicValue` machinery, then its dynamic
        value is returned from this function. Otherwise the value
        of the :attr:`id` attribute is returned.

        .. note::

            The ID of a :class:`Packet` is not checked for
            equality between :class:`Packet`\s.

        Warnings
        --------
        The ID of a :class:`Packet` must be both hashable and equality
        comparable for various facilities involving IDs to work correctly.

        Many protocols have a :class:`Packet.Header` prefixing each
        :class:`Packet` with just an ID. To model this common protocol,
        one can do something like this::

            >>> import pak
            >>> class MyPacket(pak.Packet):
            ...     id = 3
            ...     array: pak.Int16[2]
            ...     class Header(pak.Packet.Header):
            ...         id: pak.Int8
            ...
            >>> MyPacket(array=[1, 2]).pack()
            b'\x03\x01\x00\x02\x00'

        Parameters
        ----------
        ctx : :class:`Packet.Context`
            The context for the :class:`Packet`.

        Returns
        -------
        any
            By default returns ``None``, and if the ID is ``None``
            then the :class:`Packet` shouldn't be considered when
            looking up :class:`Packet`\s from their ID.

            Otherwise the ID of the :class:`Packet`.
        """

        return None

    @classmethod
    def _init_id(cls):
        # Don't do anything with the ID if it's already a classmethod.
        if inspect.ismethod(cls.id):
            return

        # Transform normal values and dynamic values into a classmethod.
        id = DynamicValue(inspect.getattr_static(cls, "id"))

        if isinstance(id, DynamicValue):
            @classmethod
            def real_id(cls, *, ctx=None):
                """Gets the ID of the packet."""

                if ctx is None:
                    ctx = cls.Context()

                return id.get(ctx=ctx)
        else:
            @classmethod
            def real_id(cls, *, ctx=None):
                """Gets the ID of the packet."""

                return id

        cls.id = real_id

    @classmethod
    def _init_fields_from_annotations(cls):
        # TODO: Figure out a good way to have generic
        # anonymous field names.

        annotations = util.annotations(cls)

        cls._fields = {}
        for base in cls.mro()[1:]:
            if not issubclass(base, Packet):
                continue

            for attr, attr_type in base.enumerate_field_types():
                if attr in cls._fields:
                    raise DuplicateFieldError(cls, attr)

                cls._fields[attr] = attr_type

        for attr, attr_type in annotations.items():
            if attr in cls.RESERVED_FIELDS:
                raise ReservedFieldError(cls, attr)

            if attr in cls._fields:
                raise DuplicateFieldError(cls, attr)

            real_type = Type(attr_type)

            cls._fields[attr] = real_type

            # Only add the Type descriptor
            # if there isn't already something
            # in its place (like a property).
            if not hasattr(cls, attr):
                descriptor = real_type.descriptor()

                # Set the name manually because '__set_name__'
                # only gets called on type construction, and
                # furthermore before __init_subclass__ is called.
                descriptor.__set_name__(cls, attr)

                setattr(cls, attr, descriptor)

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        cls._init_id()
        cls._init_fields_from_annotations()

    def __init__(self, *, ctx=None, **fields):
        type_ctx = self.type_ctx(ctx)
        for attr, attr_type in self.enumerate_field_types():
            if attr in fields:
                setattr(self, attr, fields.pop(attr))
            else:
                default = attr_type.default(ctx=type_ctx)
                try:
                    setattr(self, attr, default)
                except AttributeError:
                    # If trying to set a default fails
                    # (like if the attribute is read-only)
                    # then just move on.
                    pass

        # All the fields should be used up by the end of the
        # above loop because we pop them out.
        if len(fields) > 0:
            raise TypeError(f"Unexpected keyword arguments for '{type(self).__qualname__}': {fields}")

    def header(self, *, ctx=None):
        """Gets the :class:`Packet.Header` for the :class:`Packet`.

        Parameters
        ----------
        ctx : :class:`Packet.Context`
            The context for the :class:`Packet`.

        Returns
        -------
        :class:`Packet.Header`
            The header for the :class:`Packet`.

        Examples
        --------
        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     id = 1
        ...     class Header(pak.Packet.Header):
        ...         id: pak.UInt8
        ...
        >>> MyPacket().header()
        MyPacket.Header(id=1)
        """

        return self.Header(self, ctx=ctx)

    @classmethod
    def unpack(cls, buf, *, ctx=None):
        """Unpacks a :class:`Packet` from raw data.

        .. note::

            This doesn't unpack the header, as you need to unpack
            the :class:`Packet.Header` to determine the correct
            :class:`Packet` to unpack in the first place.

        Parameters
        ----------
        buf : file object or :class:`bytes` or :class:`bytearray`
            The buffer containing the raw data.
        ctx : :class:`Packet.Context`
            The context for the :class:`Packet`.

        Returns
        -------
        :class:`Packet`
            The :class:`Packet` marshaled from the raw data.

        Examples
        --------
        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     hello: pak.RawByte[5]
        ...     world: pak.RawByte[5]
        ...
        >>> MyPacket.unpack(b"HelloWorld")
        MyPacket(hello=bytearray(b'Hello'), world=bytearray(b'World'))
        """

        self = object.__new__(cls)

        buf = util.file_object(buf)

        type_ctx = self.type_ctx(ctx)
        for attr, attr_type in cls.enumerate_field_types():
            value = attr_type.unpack(buf, ctx=type_ctx)

            try:
                setattr(self, attr, value)

            except AttributeError:
                # If trying to set an unpacked value fails
                # (like if the attribute is read-only)
                # then just move on.
                pass

        return self

    def pack_without_header(self, *, ctx=None):
        r"""Packs a :class:`Packet` to raw data, excluding the :class:`Packet.Header`.

        Parameters
        ----------
        ctx : :class:`Packet.Context`
            The context for the :class:`Packet`.

        Returns
        -------
        :class:`bytes`
            The raw data marshaled from the :class:`Packet`, excluding the header.

        Examples
        --------
        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     id = 0xFF
        ...     array: pak.UInt8[pak.UInt8]
        ...     class Header(pak.Packet.Header):
        ...         id: pak.UInt8
        ...
        >>> p = MyPacket(array=[0, 1, 2, 3])
        >>> p.pack_without_header()
        b'\x04\x00\x01\x02\x03'
        """

        type_ctx = self.type_ctx(ctx)

        return b"".join(
            attr_type.pack(value, ctx=type_ctx)
            for attr_type, value in self.field_types_and_values()
        )

    def pack(self, *, ctx=None):
        r"""Packs a :class:`Packet` to raw data.

        .. note::

            This does pack the :class:`Packet.Header`, unlike :meth:`unpack`.

            First the :class:`Packet.Header` is gotten from :meth:`header`,
            then it is packed, and then :meth:`pack_without_header` is called.

        Parameters
        ----------
        ctx : :class:`Packet.Context`
            The context for the :class:`Packet`.

        Returns
        -------
        :class:`bytes`
            The raw data marshaled from the :class:`Packet`.

        Examples
        --------
        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     id = 0xFF
        ...     array: pak.UInt8[pak.UInt8]
        ...     class Header(pak.Packet.Header):
        ...         id: pak.UInt8
        ...
        >>> p = MyPacket(array=[0, 1, 2, 3])
        >>> p.pack()
        b'\xff\x04\x00\x01\x02\x03'
        """

        packed_header = self.header(ctx=ctx).pack(ctx=ctx)

        return packed_header + self.pack_without_header(ctx=ctx)

    def type_ctx(self, ctx):
        """Converts a :class:`Packet.Context` to a :class:`.Type.Context`.

        Parameters
        ----------
        ctx : :class:`Packet.Context` or ``None``
            The context for the :class:`Packet`.

        Returns
        -------
        :class:`.Type.Context`
            The context for a :class:`~.Type`.
        """

        if ctx is None:
            ctx = self.Context()

        return Type.Context(self, ctx=ctx)

    @classmethod
    def field_names(cls):
        """Gets the names of the fields of the :class:`Packet`.

        Returns
        -------
        iterable
            Each element is the name of a field.

        Examples
        --------
        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     attr1: pak.Int8
        ...     attr2: pak.Int16
        ...
        >>> for name in MyPacket.field_names():
        ...     print(name)
        ...
        attr1
        attr2
        """

        return cls._fields.keys()

    @classmethod
    def field_types(cls):
        r"""Gets the :class:`~.Type`\s of each field of the :class:`Packet`.

        Returns
        -------
        iterable
            Each element is the :class:`~.Type` of a field.

        Examples
        --------
        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     attr1: pak.Int8
        ...     attr2: pak.Int16
        ...
        >>> for type in MyPacket.field_types():
        ...     print(type.__qualname__)
        ...
        Int8
        Int16
        """

        return cls._fields.values()

    def field_values(self):
        """Gets the values of each field of the :class:`Packet`.

        Returns
        -------
        iterable
            Each element is the value of a field.

        Examples
        --------
        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     attr1: pak.Int8
        ...     attr2: pak.Int16
        ...
        >>> p = MyPacket(attr1=1, attr2=2)
        >>> for value in p.field_values():
        ...     print(value)
        ...
        1
        2
        """

        for field in self.field_names():
            yield getattr(self, field)

    def field_types_and_values(self):
        r"""Gets the :class:`~.Type`\s and values of each field of the :class:`Packet`.

        Returns
        -------
        iterable
            Each element is a (``field_type``, ``field_value``) pair.

        Examples
        --------
        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     attr1: pak.Int8
        ...     attr2: pak.Int16
        ...
        >>> p = MyPacket(attr1=1, attr2=2)
        >>> for type, value in p.field_types_and_values():
        ...     print(f"{type.__qualname__}; {value}")
        ...
        Int8; 1
        Int16; 2
        """

        for field, type in self.enumerate_field_types():
            yield type, getattr(self, field)

    @classmethod
    def enumerate_field_types(cls):
        r"""Enumerates the :class:`~.Type`\s of the fields of the :class:`Packet`.

        Returns
        -------
        iterable
            Each element of the iterable is a (``field_name``, ``field_type``) pair.

        Examples
        --------
        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     attr1: pak.Int8
        ...     attr2: pak.Int16
        ...
        >>> for attr, attr_type in MyPacket.enumerate_field_types():
        ...     print(f"{attr}: {attr_type.__qualname__}")
        ...
        attr1: Int8
        attr2: Int16
        """

        return cls._fields.items()

    def enumerate_field_values(self):
        """Enumerates the values of the fields of the :class:`Packet`.

        Returns
        -------
        iterable
            Each element of the iterable is a (``field_name``, ``field_value``) pair.

        Examples
        --------
        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     attr1: pak.Int8
        ...     attr2: pak.Int16
        ...
        >>> p = MyPacket(attr1=1, attr2=2)
        >>> for attr, value in p.enumerate_field_values():
        ...     print(f"{attr}: {value}")
        ...
        attr1: 1
        attr2: 2
        """

        for attr in self._fields:
            yield attr, getattr(self, attr)

    def enumerate_field_types_and_values(self):
        r"""Enumerates the :class:`~.Type`\s and values of the fields of the :class:`Packet`.

        Returns
        -------
        iterable
            Each element of the iterable is a (``field_name``, ``field_type``, ``field_value``) triplet.

        Examples
        --------
        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     attr1: pak.Int8
        ...     attr2: pak.Int16
        ...
        >>> p = MyPacket(attr1=1, attr2=2)
        >>> for attr, attr_type, value in p.enumerate_field_types_and_values():
        ...     print(f"{attr}: {attr_type.__qualname__}; {value}")
        ...
        attr1: Int8; 1
        attr2: Int16; 2
        """

        for attr, attr_type in self.enumerate_field_types():
            yield attr, attr_type, getattr(self, attr)

    def size(self, *, ctx=None):
        """Gets the cumulative size of the fields of the :class:`Packet`.

        .. note::

            The header is not included in the size.

        Returns
        -------
        :class:`int`
            The cumulative size of the fields of the :class:`Packet`.

        Examples
        --------
        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     array:   pak.Int16[2]
        ...     float64: pak.Float64
        ...
        >>> MyPacket().size()
        12
        """

        type_ctx = self.type_ctx(ctx)

        return sum(
            attr_type.size(attr_value, ctx=type_ctx)

            for attr_type, attr_value in self.field_types_and_values()
        )

    @classmethod
    @util.cache
    def subclasses(cls):
        r"""Gets the recursive subclasses of the :class:`Packet`.

        Useful for when you have categories of :class:`Packet`\s, such as
        serverbound and clientbound, and so you can have an empty class like

        ::

            class ServerboundPacket(Packet):
                pass

        which all serverbound :class:`Packet`\s would inherit from,
        and then use :meth:`subclasses` to automatically get all the
        serverbound :class:`Packet`\s.

        .. note::

            This method is decorated with :func:`util.cache() <.decorators.cache>`. In particular
            this means you can't generate a new subclass after calling this
            and have it be returned from :meth:`subclasses` the next time you
            call it.

        Returns
        -------
        :class:`frozenset`
            The recursive subclasses of the :class:`Packet`.
        """

        return util.subclasses(cls)

    @classmethod
    @util.cache
    def subclass_with_id(cls, id, *, ctx=None):
        """Gets the subclass with the equivalent ID.

        Parameters
        ----------
        id
            The ID of the :class:`Packet`.

            .. seealso::
                :meth:`Packet.id`
        ctx : :class:`Packet.Context` or ``None``
            The context for  the :class:`Packet`.

        Returns
        -------
        subclass of :class:`Packet` or ``None``
            If ``None``, then there is no :class:`Packet` whose
            ID is ``id``. Otherwise returns the appropriate subclass.
        """

        if ctx is None:
            ctx = cls.Context()

        for subclass in cls.subclasses():
            subclass_id = subclass.id(ctx=ctx)
            if subclass_id is not None and subclass_id == id:
                return subclass

        return None

    def __eq__(self, other):
        # ID and header are not included in equality.

        if self._fields != other._fields:
            return False

        return all(
            value == other_value
            for value, other_value in
            zip(self.field_values(), other.field_values())
        )

    # TODO: Should we implement '__hash__' even though Packets are not immutable?
    # Technically mutability is contextual and not a fact of a type.

    def __repr__(self):
        return (
            f"{type(self).__qualname__}("

            +

            ", ".join(
                f'{attr}={repr(value)}'
                for attr, value in self.enumerate_field_values()
            )

            +

            ")"
        )

# Will be set to 'Packet.Header'.
class _Header(Packet):
    r"""The header for a :class:`Packet`.

    Must be accessible from the ``Header`` attribute
    of your :class:`Packet` class, such as ``MyPacket.Header``.

    For example::

        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     byte: pak.Int8
        ...     short: pak.Int16
        ...     class Header(pak.Packet.Header):
        ...         size: pak.UInt8
        ...         byte: pak.Int8
        ...
        >>> MyPacket.Header(MyPacket(byte=1))
        MyPacket.Header(size=3, byte=1)
        >>> # Alternatively, you may use the 'Packet.header' method
        >>> MyPacket(byte=1).header()
        MyPacket.Header(size=3, byte=1)

    To unpack the header, simply call :meth:`Packet.unpack`
    on the header class, like so::

        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     byte: pak.Int8
        ...     short: pak.Int16
        ...     class Header(pak.Packet.Header):
        ...         size: pak.UInt8
        ...         byte: pak.Int8
        ...
        >>> MyPacket.Header.unpack(b"\x03\x01")
        MyPacket.Header(size=3, byte=1)

    .. note::

        Subclasses of :class:`Packet.Header` (i.e. all :class:`Packet` headers)
        may not have headers of their own.

    Parameters
    ----------
    packet : :class:`Packet` or ``None``
        The :class:`Packet` for which the header is for.

        Each field of the header will be acquired from ``packet``.
        If the corresponding attribute in ``packet`` is a method,
        then it will be called with the ``ctx`` keyword argument.

        If not ``None``, then no ``**fields`` must be passed.
    ctx : :class:`Packet.Context`
        The context for the :class:`Packet`.
    **fields
        The names and corresponding values of the fields
        of the :class:`Packet`.

        If ``packet`` is not ``None``, then no fields
        may be passed.

    Raises
    ------
    :exc:`TypeError`
        If ``packet`` is not ``None`` and any ``**fields`` are passed.
    """

    @staticmethod
    def _get_field(packet, name, *, ctx):
        field = getattr(packet, name)
        if inspect.ismethod(field):
            field = field(ctx=ctx)

        return field

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # TODO: Is this correct behavior, or should we just not check this?
        # Technically it's only bad if a packet header has its own header which
        # would marshal to anything but empty bytes.
        if cls.Header is not Packet.Header:
            raise TypeError(f"'{cls.__qualname__}' may have no header of its own")

    # TODO: When Python 3.7 support is dropped, make 'packet' positional-only.
    def __init__(self, packet=None, *, ctx=None, **fields):
        if packet is not None:
            if len(fields) != 0:
                raise TypeError("'Packet.Header' cannot be passed both a 'Packet' and normal fields")

            fields = {
                name: self._get_field(packet, name, ctx=ctx)

                for name in self.field_names()
            }

        super().__init__(ctx=ctx, **fields)

    def pack(self, *, ctx=None):
        """Overrides :meth:`Packet.pack` to call :meth:`Packet.pack_without_header`
        to avoid infinite recursion when packing.
        """

        return self.pack_without_header(ctx=ctx)

# Set appropriate naming for 'Packet.Header'.
_Header.__name__     = "Header"
_Header.__qualname__ = "Packet.Header"
Packet.Header        = _Header

class GenericPacket(Packet):
    """A generic collection of data.

    Reads all of the data in the buffer passed to it.
    """

    data: RawByte[None]
