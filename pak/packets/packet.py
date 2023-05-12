r"""Base code for :class:`.Packet`\s."""

import copy
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

# The following are classmethods that will be
# installed by 'Packet._init_id' depending on
# the sort of ID set in the packet definition.

@classmethod
def _id_wrapper_classmethod(cls, *, ctx=None):
    if ctx is None:
        ctx = cls.Context()

    return cls._wrapped_id(ctx=ctx)

@classmethod
def _id_wrapper_dynamic_value(cls, *, ctx=None):
    if ctx is None:
        ctx = cls.Context()

    return cls._wrapped_id.get(ctx=ctx)

@classmethod
def _id_wrapper_static_value(cls, *, ctx=None):
    return cls._wrapped_id

class Packet:
    r"""A collection of values that can be marshaled to and from
    raw data using :class:`.Type`\s.

    The difference between a :class:`Packet` and a :class:`.Type`
    is that :class:`.Type`\s only define how to marshal values
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
        # This metaclass isn't *strictly* needed to check if a 'Packet.Context'
        # provides a '__hash__' implementation, since checking
        # 'cls.__hash__ is Packet.Context.__hash__' in '__init_subclass__' would
        # likely be sufficient to provide *enough* safety. However that would
        # restrict certain ways of defining an implementation, i.e. doing
        # '__hash__ = Packet.Context.__hash__', and would not enforce the user
        # thinking about hashability in all cases, i.e. when inheriting from a
        # class that inherits from 'Packet.Context'.

        def __new__(cls, name, bases, namespace):
            if namespace.get("__hash__") is None:
                raise TypeError(f"'{namespace['__qualname__']}' must provide an implementation of '__hash__'")

            if namespace.get("__eq__") is None:
                raise TypeError(f"'{namespace['__qualname__']}' must provide an implementation of '__eq__'")

            return super().__new__(cls, name, bases, namespace)

    class Context(metaclass=_ContextMeta):
        r"""The context for a :class:`Packet`.

        :class:`Packet.Context`\s are used to pass arbitrary data
        to :class:`Packet` operations, typically just being wrapped
        in a :class:`.Type.Context` and sent off to :class:`.Type`
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
            ...         def __eq__(self, other):
            ...             return self.info == other.info
            ...

        When no :class:`Packet.Context` is provided to :class:`Packet`
        operations that may accept one, then your subclass is attempted
        to be default constructed and used instead.

        .. warning::

            Subclasses **must** be properly hashable. Accordingly, this
            means that subclasses should also be immutable. Therefore,
            the constructor of :class:`Packet.Context` sets the constructed
            object to be immutable.

            If a subclass of :class:`Packet.Context` does not provide its
            own ``__hash__`` implementation, then a :exc:`TypeError` is raised.
            Since all hashable objects should also be equality comparable,
            if a subclass of :class:`Packet.Context` does not provide its own
            ``__eq__`` implementation, then a :exc:`TypeError` is raised as well.
        """

        # NOTE: It may be beneficial to allow the user to specify
        # a certain mode for handling unspecified contexts. The default
        # could be that a context is not necessary to specify, and
        # another could be that if a context is not specified, an error
        # is raised. The former would retain the ease of use with not
        # needing to specify a context all the time, and the latter would
        # allow more complex projects to verify their correctness (that
        # they forward contexts properly) more easily. Before doing this
        # however I would want to verify that it is indeed a severe enough
        # problem, and think of the best API for it, which would require
        # users who are not me to chime in.

        def __init__(self):
            self._immutable_flag = True

        def __setattr__(self, attr, value):
            if hasattr(self, "_immutable_flag"):
                raise TypeError(f"'{type(self).__qualname__}' is immutable")

            super().__setattr__(attr, value)

        def __hash__(self):
            # A default 'Packet.Context' has no unique information.
            return 0

        def __eq__(self, other):
            # All objects of type 'Packet.Context' are equal.

            if type(other) is not type(self):
                return NotImplemented

            return True

    # The fields dictionary for 'Packet'.
    #
    # Since 'Packet' has no annotations, and has no parent to fall back on
    # for its fields, we define it here.
    _fields = {}

    # Will be replaced after 'Packet' is defined.
    #
    # This dummy class is defined here to have the
    # docs properly ordered.
    #
    # 'Packet.Header' needs to be defined after
    # 'Packet' because 'Packet.Header' inherits
    # from it.
    class Header:
        pass

    #: The reserved field names for :class:`Packet`.
    #:
    #: Subclasses are able to define their own
    #: reserved field names, which will be
    #: combined with the reserved field names
    #: of their parent classes.
    #:
    #: If a :class:`Packet` defines a field whose
    #: name is reserved by any of its parent
    #: classes, then a :exc:`ReservedFieldError`
    #: will be raised.
    RESERVED_FIELDS = [
        "ctx",
    ]

    @classmethod
    def _id_wrapper(cls, *, ctx=None):
        return None

    @classmethod
    def id(cls, *, ctx=None):
        r"""Gets the ID of the :class:`Packet`.

        Lots of packet protocols specify :class:`Packet`\s with
        an ID to determine what type of :class:`Packet` should
        be read. Unless overridden, :class:`Packet` has no
        meaningful ID.

        When overriding this method with a classmethod, you do
        not need to default the ``ctx`` parameter, you can just
        have it like so::

            class MyPacket(pak.Packet):
                @classmethod
                def id(cls, *, ctx):
                    ...

        The case where no ``ctx`` is specified when calling this
        method will be handled for you.

        If the :attr:`id` attribute of a subclass is enrolled
        in the :class:`.DynamicValue` machinery, then its dynamic
        value is returned from this function. Otherwise the value
        of the :attr:`id` attribute is returned.

        .. note::

            The ID of a :class:`Packet` is not checked for
            equality between :class:`Packet`\s.

        .. warning::

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

        return cls._id_wrapper(ctx=ctx)

    @classmethod
    @util.cache
    def GenericWithID(cls, id):
        r"""Generates a subclass of the :class:`Packet` class and :class:`GenericPacket` with the specified ID.

        .. note::

            This method is decorated with :func:`util.cache() <.decorators.cache>`.

            This means that when called twice with the same ID,
            then the exact same class will be returned.

        Parameters
        ----------
        id
            The ID of the generated :class:`GenericPacket`.

        Returns
        -------
        :class:`GenericPacket`
            The generated :class:`GenericPacket`.

        Examples
        --------
        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     class Header(pak.Packet.Header):
        ...         id: pak.Int8
        ...
        >>> generic = MyPacket.GenericWithID(1)
        >>> generic is MyPacket.GenericWithID(1)
        True
        >>> issubclass(generic, MyPacket)
        True
        >>> issubclass(generic, pak.GenericPacket)
        True
        >>> packet = generic.unpack(b"generic data")
        >>> packet
        MyPacket.GenericWithID(1)(data=bytearray(b'generic data'))
        >>> packet.pack()
        b'\x01generic data'
        """

        return type(f"{cls.__qualname__}.GenericWithID({repr(id)})", (GenericPacket, cls), dict(
            id = id,

            __module__ = cls.__module__,
        ))

    @classmethod
    @util.cache
    def EmptyWithID(cls, id):
        r"""Generates an empty subclass of the :class:`Packet` class with the specified ID.

        .. note::

            This method is decorated with :func:`util.cache() <.decorators.cache>`.

            This means that when called twice with the same ID,
            then the exact same class will be returned.

        Parameters
        ----------
        id
            The ID of the generated :class:`Packet`.

        Returns
        -------
        :class:`Packet`
            The generated :class:`Packet`.

        Examples
        --------
        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     class Header(pak.Packet.Header):
        ...         id: pak.Int8
        ...
        >>> empty = MyPacket.EmptyWithID(1)
        >>> empty is MyPacket.EmptyWithID(1)
        True
        >>> issubclass(empty, MyPacket)
        True
        >>> packet = empty.unpack(b"any data")
        >>> packet
        MyPacket.EmptyWithID(1)()
        >>> packet.pack()
        b'\x01'
        """

        return type(f"{cls.__qualname__}.EmptyWithID({repr(id)})", (cls,), dict(
            id = id,

            __module__ = cls.__module__,
        ))

    @classmethod
    def _init_id(cls):
        # Here we take the ID that was set through
        # the 'id' attribute and wrap it sufficiently
        # that packet IDs can still be uniformly accessed
        # through the normal 'Packet.id' classmethod.
        #
        # We delete the 'id' attribute primarily to
        # stop the classmethod from appearing in
        # autodoc'ed subclasses.
        #
        # We could use a metaclass and just look in
        # the supplied namespace to see if the ID was
        # set in the class definition and then just
        # never pass that on when we really construct
        # the type, but I feel that this is the cleaner
        # option.

        id = cls.id

        if inspect.ismethod(id):
            # Don't do anything if the ID hasn't been set.
            if id.__func__ is Packet.id.__func__:
                return

            # Make sure that we are handling a classmethod
            # bound to our class.
            if id.__self__ is cls:
                # Set the actual 'classmethod' object and not
                # the bound method.
                cls._wrapped_id = inspect.getattr_static(cls, "id")
                cls._id_wrapper = _id_wrapper_classmethod

                del cls.id
                return

        del cls.id

        id = DynamicValue(id)
        cls._wrapped_id = id

        if isinstance(id, DynamicValue):
            cls._id_wrapper = _id_wrapper_dynamic_value
        else:
            cls._id_wrapper = _id_wrapper_static_value

    @classmethod
    def _init_fields_from_annotations(cls):
        # It may be beneficial to have packet fields be
        # slot attributes. It would however require a
        # metaclass as slot attributes can't be added
        # after class initialization. I in fact implemented
        # this, but found that slot attributes and certain
        # aspects of packets do not (and mayhaps *cannot*)
        # interact well, namely overlaying packet fields
        # on top of properties and packet headers. So
        # unless there is a highly compelling reason to
        # remove or fundamentally alter these things,
        # packet fields being slots will remain unimplemented.

        annotations = util.annotations(cls)

        cls._fields = {}
        reserved_fields = set(cls.RESERVED_FIELDS)
        for base in cls.mro()[1:]:
            if not issubclass(base, Packet):
                continue

            reserved_fields.update(base.RESERVED_FIELDS)

            for attr, attr_type in base.enumerate_field_types():
                if attr in cls._fields:
                    raise DuplicateFieldError(cls, attr)

                cls._fields[attr] = attr_type

        for attr, attr_type in annotations.items():
            if attr in reserved_fields:
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
        # Lazy initialized when needed.
        type_ctx = None

        for attr, attr_type in self.enumerate_field_types():
            if attr in fields:
                setattr(self, attr, fields.pop(attr))
            else:
                if type_ctx is None:
                    type_ctx = self.type_ctx(ctx)

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

        # This is necessary because when the header tries to create
        # its own context, then it would use the incorrect class to
        # potentially default construct the context.
        if ctx is None:
            ctx = self.Context()

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

    def make_immutable(self):
        """Makes the :class:`Packet` immutable.

        This may be useful for situations where e.g. you pass
        the same :class:`Packet` instance to several functions
        and want to make sure that those functions don't change
        the fields of the :class:`Packet` for the other functions
        being passed the instance. For example if you had::

            import pak

            class MyPacket(pak.Packet):
                field: pak.Int8

            def foo(packet):
                packet.field = 2

            def bar(packet):
                assert packet.field == 1

            p = MyPacket(field=1)

            foo(p)
            bar(p)

        Then the assert within ``bar`` would fail, since ``foo``
        changed ``p.field`` to ``2``. If ``p`` is made immutable
        however, an error will be raised in ``foo``, preventing
        any hard-to-track-down errors.

        Examples
        --------
        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     field: pak.Int8
        ...
        >>> p = MyPacket(field=1)
        >>> p.field = 2
        >>> p
        MyPacket(field=2)
        >>> p.make_immutable()
        >>> p.field = 3
        Traceback (most recent call last):
        ...
        AttributeError: This 'MyPacket' instance has been made immutable
        """

        self._immutable_flag = True

    def __setattr__(self, attr, value):
        if hasattr(self, "_immutable_flag"):
            raise AttributeError(f"This '{type(self).__qualname__}' instance has been made immutable")

        super().__setattr__(attr, value)

    def copy(self, **new_attrs):
        """Makes a mutable copy of the :class:`Packet`.

        .. seealso::

            :meth:`immutable_copy`

        Parameters
        ----------
        **new_attrs
            The new attributes to set on the copy.

        Returns
        -------
        :class:`Packet`
            The copied :class:`Packet`.

        Examples
        --------
        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     field: pak.Int8
        ...
        >>> orig = MyPacket(field=1)
        >>> copy = orig.copy()
        >>> copy == orig
        True
        >>> copy is not orig
        True
        >>>
        >>> # Attributes that aren't fields will also be copied:
        >>> orig = MyPacket(field=2)
        >>> orig.custom_attr = "custom"
        >>> copy = orig.copy()
        >>> copy == orig
        True
        >>> copy.custom_attr
        'custom'
        >>>
        >>> # The copy can be mutated:
        >>> copy.field = 3
        >>> copy
        MyPacket(field=3)
        >>>
        >>> # You can set new fields on the copy by passing keyword arguments:
        >>> orig.copy(field=4)
        MyPacket(field=4)
        """

        copied = copy.deepcopy(self)

        try:
            # Try to remove the mutable flag.
            del copied._immutable_flag

        except AttributeError:
            # If that fails, we were already mutable.
            pass

        for name, value in new_attrs.items():
            setattr(copied, name, value)

        return copied

    def immutable_copy(self, **new_attrs):
        """Makes an immutable copy of the :class:`Packet`.

        .. seealso::

            :meth:`copy`

        Parameters
        ----------
        **new_attrs
            The new attributes to set on the copy.

        Returns
        -------
        :class:`Packet`
            The copied, immutable :class:`Packet`.

        Examples
        --------
        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     field: pak.Int8
        ...
        >>> orig = MyPacket(field=1)
        >>> copy = orig.immutable_copy()
        >>> copy == orig
        True
        >>> copy is not orig
        True
        >>>
        >>> # Attributes that aren't fields will also be copied:
        >>> orig = MyPacket(field=2)
        >>> orig.custom_attr = "custom"
        >>> copy = orig.immutable_copy()
        >>> copy == orig
        True
        >>> copy is not orig
        True
        >>> copy.custom_attr
        'custom'
        >>>
        >>> # You cannot modify the copy:
        >>> copy.field = 3
        Traceback (most recent call last):
        ...
        AttributeError: This 'MyPacket' instance has been made immutable
        >>>
        >>> # You can however set fields that the immutable copy will have:
        >>> copy = orig.immutable_copy(field=3)
        >>> copy
        MyPacket(field=3)
        >>> # This copy is still immutable:
        >>> copy.field = 4
        Traceback (most recent call last):
        ...
        AttributeError: This 'MyPacket' instance has been made immutable
        """

        copied = self.copy(**new_attrs)

        copied.make_immutable()

        return copied

    def type_ctx(self, ctx):
        """Converts a :class:`Packet.Context` to a :class:`.Type.Context`.

        Parameters
        ----------
        ctx : :class:`Packet.Context` or ``None``
            The context for the :class:`Packet`.

        Returns
        -------
        :class:`.Type.Context`
            The context for a :class:`.Type`.
        """

        if ctx is None:
            ctx = self.Context()

        return Type.Context(self, ctx=ctx)

    @classmethod
    def has_field(cls, name):
        """Gets whether the :class:`Packet` has a certain field.

        Parameters
        ----------
        name : :class:`str`
            The name of the field to check for.

        Returns
        -------
        :class:`bool`
            Whether the :class:`Packet` has a field with the specified name.

        Examples
        --------
        >>> import pak
        >>> class MyPacket(pak.Packet):
        ...     defined_field: pak.UInt8
        ...
        >>> MyPacket.has_field("defined_field")
        True
        >>> MyPacket.has_field("undefined_field")
        False
        """

        return name in cls._fields

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
        r"""Gets the :class:`.Type`\s of each field of the :class:`Packet`.

        Returns
        -------
        iterable
            Each element is the :class:`.Type` of a field.

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
        r"""Gets the :class:`.Type`\s and values of each field of the :class:`Packet`.

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
        r"""Enumerates the :class:`.Type`\s of the fields of the :class:`Packet`.

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
        r"""Enumerates the :class:`.Type`\s and values of the fields of the :class:`Packet`.

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

    @util.class_or_instance_method
    def size(cls, *, ctx=None):
        """Gets the cumulative size of the fields of the :class:`Packet`.

        This may be called either as a :class:`classmethod` or as an instance
        method. When called as a :class:`classmethod`, the static size of
        the :class:`Packet` is attempted to be calculated, irrespective of
        any values. When called as an instance method, then the values of
        the fields of the :class:`Packet` are used to calculate the size.

        .. note::

            The header is not included in the size.

        Parameters
        ----------
        ctx : :class:`Packet.Context`
            The context for the :class:`Packet`.

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
        >>> MyPacket.size()
        12
        """

        if ctx is None:
            ctx = cls.Context()

        type_ctx = Type.Context(ctx=ctx)

        return sum(field_type.size(ctx=type_ctx) for field_type in cls.field_types())

    def _size_impl(self, *, ctx=None):
        # NOTE: We have this separate function so that
        # we can get the size of a 'Packet.Header' instance.

        type_ctx = self.type_ctx(ctx)

        return sum(
            attr_type.size(attr_value, ctx=type_ctx)

            for attr_type, attr_value in self.field_types_and_values()
        )

    @size.instance_method
    def size(self, *, ctx=None):
        return self._size_impl(ctx=ctx)

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

        if not isinstance(other, Packet):
            return NotImplemented

        if self._fields != other._fields:
            return False

        return all(
            value == other_value
            for value, other_value in
            zip(self.field_values(), other.field_values())
        )

    # NOTE: We do not implement '__hash__' since Packets are not immutable by default.
    # Technically mutability is contextual and not a fact of a type.
    # However, making Packets hashable would just not line up with proper
    # semantics in any genuine use case that requires 'Packet' itself to be hashable.
    # Users may always implement hashing themselves.
    __hash__ = None

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
        may not have headers or contexts of their own.

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

        # NOTE: Technically it's only bad if a packet header has its own header
        # which would marshal to anything but empty bytes. However, potential
        # headers which would marshal to empty bytes but still have 'genuine'
        # values are pathological cases which I have no interest in supporting.
        if cls.Header is not Packet.Header:
            raise TypeError(f"'{cls.__qualname__}' may have no header of its own")

        # Headers receive the context of their body packets.
        if cls.Context is not Packet.Context:
            raise TypeError(f"'{cls.__qualname__}' may have no context of its own")

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

# Remove access through '_Header' to stop it from showing in docs.
del _Header

class GenericPacket(Packet):
    """A generic collection of data.

    Reads all of the data in the buffer passed to it.
    """

    data: RawByte[None]
