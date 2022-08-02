r"""Base code for :class:`.Type`\s."""

import abc
import inspect
import copy
import functools

from .. import util
from ..dyn_value import DynamicValue

__all__ = [
    "NoStaticSizeError",
    "Type",
]

class NoStaticSizeError(Exception):
    """An error indicating a :class:`Type` has no static size.

    Parameters
    ----------
    type_cls : subclass of :class:`Type`
        The :class:`Type` which has no static size.
    """

    def __init__(self, type_cls):
        super().__init__(f"'{type_cls.__qualname__}' has no static size")

class Type(abc.ABC):
    r"""A definition of how to marshal raw data to and from values.

    Typically used for the types of :class:`.Packet` fields.

    When :class:`Types <Type>` are called, their :meth:`_call`
    :class:`classmethod` gets called, returning a new :class:`Type`.

    :class:`.Array` types can be constructed using indexing syntax,
    like so::

        >>> import pak
        >>> array = pak.Int8[3]
        >>> array
        <class 'pak.types.array.Int8[3]'>
        >>> array.pack([1, 2, 3])
        b'\x01\x02\x03'
        >>> array.unpack(b"\x01\x02\x03")
        [1, 2, 3]

    The object within the brackets gets passed as the ``size`` parameter
    to :class:`.Array`.

    Parameters
    ----------
    typelike
        The typelike object to convert to a :class:`Type`.

    Raises
    ------
    :exc:`TypeError`
        If ``typelike`` can't be converted to a :class:`Type`.
    """

    class Context:
        r"""The context for a :class:`Type`.

        :class:`Type.Context`\s are used to pass arbitrary data
        to :class:`Type`\s. All of that arbitrary data comes from
        the attributes of the :class:`.Packet.Context` if supplied,
        and you may access those attributes on the created :class:`Type.Context`
        as if it were the :class:`.Packet.Context` itself.

        However, a :class:`Type.Context` also contains a :attr:`packet`
        attribute which denotes the :class:`.Packet` instance for which
        a :class:`Type` utility is being used for, if any is applicable.

        .. note::

            Unlike :class:`.Packet.Context`, this should not
            be customized.

        Parameters
        ----------
        packet : :class:`.Packet`
            The packet instance that's being marshaled.
        ctx : :class:`.Packet.Context`
            The context for the packet that's being marshaled.

            Getting attributes that are not directly in the
            :class:`Type.Context` will be gotten from the
            packet context.

        Attributes
        ----------
        packet : :class:`.Packet` or ``None``
            The packet instance that's being marshaled.
        packet_ctx : :class:`.Packet.Context` or ``None``
            The context for the packet that's being marshaled.

            Getting attributes that are not directly in the
            :class:`Type.Context` will be gotten from this.
        """

        def __init__(self, packet=None, *, ctx=None):
            self.packet     = packet
            self.packet_ctx = ctx

        def __getattr__(self, attr):
            if attr in ("packet", "packet_ctx"):
                return super().__getattr__(attr)

            if self.packet_ctx is None:
                raise AttributeError(f"'{type(self).__qualname__}' object has no attribute '{attr}'")

            return getattr(self.packet_ctx, attr)

        def __setattr__(self, attr, value):
            if hasattr(self, "packet_ctx"):
                raise TypeError(f"'{type(self).__qualname__}' is immutable")

            super().__setattr__(attr, value)

        def __hash__(self):
            # We hash the identity of our packet because conceptually
            # the value of a 'Type.Context' does not depend on the
            # value of its packet, but rather its identity.
            #
            # Furthermore, 'Packet' is not hashable, so it is
            # necessary anyways.
            return hash((id(self.packet), self.packet_ctx))

        def __eq__(self, other):
            if not isinstance(other, Type.Context):
                return NotImplemented

            # We compare packets with identity to align with our
            # hash semantics, and because conceptually the value
            # of a 'Type.Context' depends on the identity of the
            # packet, not the packet's value.
            return self.packet is other.packet and self.packet_ctx == other.packet_ctx

    _typelikes = {}

    _size      = None
    _alignment = None
    _default   = None

    def __new__(cls, typelike):
        if isinstance(typelike, type) and issubclass(typelike, Type):
            return typelike

        for typelike_cls, converter in cls._typelikes.items():
            if isinstance(typelike, typelike_cls):
                return converter(typelike)

        raise TypeError(f"Object {typelike} is not typelike")

    @classmethod
    def register_typelike(cls, typelike_cls, converter):
        """Registers a class as being convertible to a :class:`Type`.

        Parameters
        ----------
        typelike_cls : :class:`type`
            The convertible type.
        converter : callable
            The object called to convert the object to a :class:`Type`.
        """

        cls._typelikes[typelike_cls] = converter

    @classmethod
    def unregister_typelike(cls, typelike_cls):
        """Unregisters a class as being convertible to a :class:`Type`.

        Parameters
        ----------
        typelike_cls : :class:`type`
            The type to unregister.
        """

        cls._typelikes.pop(typelike_cls)

    @classmethod
    def is_typelike(cls, obj):
        """Gets whether an object is typelike.

        Parameters
        ----------
        obj
            The object to check.

        Returns
        -------
        :class:`bool`
            Whether ``obj`` is typelike.
        """

        if isinstance(obj, type) and issubclass(obj, Type):
            return True

        for typelike_cls in cls._typelikes.keys():
            if isinstance(obj, typelike_cls):
                return True

        return False

    @staticmethod
    def prepare_types(func):
        """A decorator that converts arguments annotated with :class:`Type` to a :class:`Type`.

        Examples
        --------
        >>> import pak
        >>> @pak.Type.prepare_types
        ... def example(arg: pak.Type):
        ...     print(arg.__qualname__)
        ...
        >>> example(pak.Int8)
        Int8
        >>> example(None)
        EmptyType
        """

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            args_annotations, kwargs_annotations = util.bind_annotations(func, *args, **kwargs)

            new_args = [
                Type(value) if annotation is Type
                else value

                for value, annotation in args_annotations
            ]

            new_kwargs = {
                name: (
                    Type(value) if annotation is Type
                    else value
                )

                for name, (value, annotation) in kwargs_annotations.items()
            }

            return func(*new_args, **new_kwargs)

        return wrapper

    @classmethod
    def __class_getitem__(cls, index):
        """Gets an :class:`.Array` of the :class:`Type`.

        Parameters
        ----------
        index : :class:`int` or subclass of :class:`Type` or :class:`str` or :class:`function` or ``None``
            The ``size`` argument passed to :class:`.Array`.

        Examples
        --------
        >>> import pak
        >>> pak.Int8[3]
        <class 'pak.types.array.Int8[3]'>
        """

        from .array import Array

        return Array(cls, index)

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        cls._size      = DynamicValue(inspect.getattr_static(cls, "_size"))
        cls._alignment = DynamicValue(inspect.getattr_static(cls, "_alignment"))
        cls._default   = DynamicValue(inspect.getattr_static(cls, "_default"))

        # Set __new__ to _call's underlying function.
        # We don't just override __new__ instead of
        # _call so that it's more clear that calling
        # a Type is separate from actually initializing
        # an instance of Type.
        #
        # We don't use a metaclass to override construction
        # outright to simplify code. There is a possibility
        # that if the '_call' method returns an instance of
        # the type being called, it will go through to '__init__',
        # but that will raise an error in '__init__' and
        # shouldn't happen anyways.
        cls.__new__ = cls._call.__func__

    def __init__(self):
        raise TypeError("Types do not get initialized normally.")

    @classmethod
    def descriptor(cls):
        """Gets the descriptor form of the :class:`Type`.

        Returns
        -------
        :class:`Type`
            The descriptor form of the :class:`Type`.
        """

        return object.__new__(cls)

    def __set_name__(self, owner, name):
        self.attr_name = f"_{name}_type_value"

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

        return getattr(instance, self.attr_name)

    def __set__(self, instance, value):
        setattr(instance, self.attr_name, value)

    def __delete__(self, instance):
        delattr(instance, self.attr_name)

    STATIC_SIZE = util.UniqueSentinel("STATIC_SIZE")

    @classmethod
    @util.cache(force_hashable=False)
    def size(cls, value=STATIC_SIZE, *, ctx=None):
        r"""Gets the size of the :class:`Type` when packed.

        Worst case this will perform as badly as packing the value
        and getting the length of the raw data performs. However,
        :class:`Type`\s may often be able to optimize finding their
        packed sizes.

        If the :attr:`_size` attribute is any value other than ``None``,
        then that value will be returned.

        Else, If the :attr:`_size` attribute is a :class:`classmethod`,
        then it should look like this::

            @classmethod
            def _size(cls, value, *, ctx):
                return my_size

        The return value of the :class:`classmethod` will be returned from
        this method.

        Otherwise, if the :attr:`_size` attribute is a :class:`DynamicValue`,
        which it is automatically transformed into on class construction
        if applicable, then the dynamic value of that is returned.

        If any of these give a size of ``None`` or raise :exc:`NoStaticSizeError`,
        then if ``value`` is not :attr:`STATIC_SIZE`, then the value will be
        packed in order to get the size.

        Parameters
        ----------
        value : any
            If :attr:`STATIC_SIZE`, then a size irrespective of
            any value is returned, if possible.

            Otherwise,
        ctx : :class:`Type.Context` or ``None``
            The context for the :class:`Type`.

            If ``None``, then an empty :class:`Type.Context` is used.

        Returns
        -------
        :class:`int`
            The size of the :class:`Type` when packed.

        Raises
        ------
        :exc:`NoStaticSizeError`
            If the :class:`Type` has no static size but is asked for one.
        """

        if ctx is None:
            ctx = cls.Context()

        size = cls._size

        try:
            if inspect.ismethod(size):
                size = size(value, ctx=ctx)
            elif isinstance(size, DynamicValue):
                size = size.get(ctx=ctx)

        except NoStaticSizeError:
            size = None

        # If no (hopefully) performant calculation of a value's
        # packed size is available, then fallback to packing the value.
        if size is None:
            if value is cls.STATIC_SIZE:
                raise NoStaticSizeError(cls)

            size = len(cls.pack(value, ctx=ctx))

        return size

    @classmethod
    @util.cache
    def alignment(cls, *, ctx=None):
        r"""Gets the alignment of the :class:`Type`.

        The alignment of a :class:`Type` must be a power of two.

        The alignment of a :class:`Type` is typically ignored, unless
        using something that explicitly utilizes alignment, such as
        :class:`.AlignedPacket` or :class:`.AlignedCompound`.

        Furthermore, alignment only makes sense for :class:`Type`\s
        with static sizes.

        If the :attr:`_alignment` attribute is any value other
        than ``None``, then that value will be returned.

        Else, if the :attr:`_alignment` attribute is a :class:`classmethod`,
        then it should look like this::

            @classmethod
            def _alignment(cls, *, ctx):
                return my_alignment

        The return value of the :class:`classmethod` will be returned from
        this method.

        Otherwise, if the :class:`_alignment` attribute is a :class:`DynamicValue`,
        which it is automatically transformed into on class construction if
        applicable, then the dynamic value of that is returned.

        If any of these give a value of ``None``, then the :class:`Type`
        has no alignment and a :exc:`TypeError` will be raised.

        Parameters
        ----------
        ctx : :class:`Type.Context` or ``None``
            The context for the :class:`Type`.

            If ``None``, then an empty :class:`Type.Context` is used.

        Returns
        -------
        :class:`int`
            The alignment of the :class:`Type`.

        Raises
        ------
        :exc:`TypeError`
            If the :class:`Type` has no alignment.
        """

        if ctx is None:
            ctx = cls.Context()

        alignment = cls._alignment
        if inspect.ismethod(alignment):
            alignment = alignment(ctx=ctx)
        elif isinstance(alignment, DynamicValue):
            alignment = alignment.get(ctx=ctx)

        if alignment is None:
            raise TypeError(f"'{cls.__qualname__}' has no alignment")

        return alignment

    @staticmethod
    @util.cache
    def alignment_padding_lengths(*types, total_alignment, ctx=None):
        r"""Gets the length of padding after each :class:`Type` for alignment purposes.

        Should rarely be used by users. In most cases
        :class:`.AlignedCompound` or :class:`.AlignedPacket`
        should be used.

        Parameters
        ----------
        *types : subclass of :class:`Type`
            The :class:`Type`\s for which to find the padding for.
        total_alignment : :class:`int`
            The total alignment that `*types` should be aligned to,
            used for the padding at the end.
        ctx : :class:`Type.Context` or ``None``
            The context for ``*types``.

            If ``None``, then an empty :class:`Type.Context` is used.
        """

        # See https://en.wikipedia.org/wiki/Data_structure_alignment#Computing_padding
        # for more details.

        if ctx is None:
            ctx = Type.Context()

        padding_lengths = []

        offset = types[0].size(ctx=ctx)
        for t in types[1:]:
            padding_amount = -offset & (t.alignment(ctx=ctx) - 1)

            offset += t.size(ctx=ctx) + padding_amount
            padding_lengths.append(padding_amount)

        # Pad out the end with the total alignment,
        padding_lengths.append(-offset & (total_alignment - 1))

        return padding_lengths

    @classmethod
    def default(cls, *, ctx=None):
        """Gets the default value of the :class:`Type`.

        If the :attr:`_default` attribute is a :class:`classmethod`,
        then it should look like this::

            @classmethod
            def _default(cls, *, ctx):
                return my_default_value

        The return value of the :class:`classmethod` will be returned from
        this method.

        Else, if the :attr:`_default` attribute is a :class:`DynamicValue`,
        which it is automatically transformed into on class construction
        if applicable, then the dynamic value of that is returned.

        Otherwise, if the :attr:`_default` attribute is any value
        other than ``None``, a deepcopy of that value will be returned.

        Parameters
        ----------
        ctx : :class:`Type.Context` or ``None``
            The context for the :class:`Type`.

            If ``None``, then an empty :class:`Type.Context` is used.

        Returns
        -------
        any
            The default value.

        Raises
        ------
        :exc:`TypeError`
            If the :class:`Type` has no default value.
        """

        if cls._default is None:
            raise TypeError(f"'{cls.__qualname__}' has no default value")

        if ctx is None:
            ctx = cls.Context()

        if inspect.ismethod(cls._default):
            return cls._default(ctx=ctx)

        if isinstance(cls._default, DynamicValue):
            return cls._default.get(ctx=ctx)

        # Deepcopy because the default could be mutable.
        return copy.deepcopy(cls._default)

    @classmethod
    def unpack(cls, buf, *, ctx=None):
        """Unpacks raw data into its corresponding value.

        .. warning::

            Do **not** override this method. Instead override
            :meth:`_unpack`.

        Parameters
        ----------
        buf : file object or :class:`bytes` or :class:`bytearray`
            The buffer containing the raw data.
        ctx : :class:`Type.Context` or ``None``
            The context for the :class:`Type`.

            If ``None``, then an empty :class:`Type.Context` is used.

        Returns
        -------
        any
            The corresponding value of the buffer.
        """

        buf = util.file_object(buf)

        if ctx is None:
            ctx = cls.Context()

        return cls._unpack(buf, ctx=ctx)

    @classmethod
    def pack(cls, value, *, ctx=None):
        """Packs a value into its corresponding raw data.

        .. warning::

            Do **not** override this method. Instead override
            :meth:`_pack`.

        Parameters
        ----------
        value
            The value to pack.
        ctx : :class:`Type.Context` or ``None``
            The context for the :class:`Type`.

            If ``None``, then an empty :class:`Type.Context` is used.

        Returns
        -------
        :class:`bytes`
            The corresponding raw data.
        """

        if ctx is None:
            ctx = cls.Context()

        return cls._pack(value, ctx=ctx)

    @classmethod
    @abc.abstractmethod
    def _unpack(cls, buf, *, ctx):
        """Unpacks raw data into its corresponding value.

        To be overridden by subclasses.

        .. warning::

            Do not use this method directly, **always** use
            :meth:`unpack` instead.

        Parameters
        ----------
        buf : file object
            The buffer containing the raw data.
        ctx : :class:`Type.Context`
            The context for the :class:`Type`.

        Returns
        -------
        any
            The corresponding value from the buffer.
        """

        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _pack(cls, value, *, ctx):
        """Packs a value into its corresponding raw data.

        To be overridden by subclasses.

        .. warning::

            Do not use this method directly, **always** use
            :meth:`pack` instead.

        Parameters
        ----------
        value
            The value to pack.
        ctx : :class:`Type.Context`
            The context for the :class:`Type`.

        Returns
        -------
        :class:`bytes`
            The corresponding raw data.
        """

        raise NotImplementedError

    @classmethod
    def _array_static_size(cls, array_size, *, ctx):
        """Gets the static size of an :class:`.Array` with the :class:`Type` as its element.

        Parameters
        ----------
        array_size : :class:`int`
            The number of elements to get the size of.
        ctx : :class:`Type.Context`
            The context for the :class:`Type`.

        Returns
        -------
        :class:`int` or ``None``
            The size of the raw data of an :class:`.Array` of size ``array_size``.

            If ``None``, then no static size exists.

            This only includes the *body* of the :class:`.Array`,
            not length prefixes or anything of that sort.
        """

        return array_size * cls.size(ctx=ctx)

    @classmethod
    def _array_default(cls, array_size, *, ctx):
        """Gets the default value for an :class:`.Array` with the :class:`Type` as its element.

        Parameters
        ----------
        array_size : :class:`int`
            The number of elements to create a default for.
        ctx : :class:`Type.Context`
            The context for the :class:`Type`.

        Returns
        -------
        any
            The default value for an :class:`.Array` with
            the :class:`Type` as its element.
        """

        return [cls.default(ctx=ctx) for x in range(array_size)]

    @classmethod
    def _array_unpack(cls, buf, array_size, *, ctx):
        """Unpacks an :class:`.Array` with the :class:`Type` as its element.

        Parameters
        ----------
        buf : file object
            The buffer containing the raw data.
        array_size : :class:`int` or ``None``
            The number of elements to unpack.

            If ``None``, then as many elements
            as possible should be unpacked from
            ``buf``.
        ctx : :class:`Type.Context`
            The context for the :class:`Type`.

        Returns
        -------
        any
            The corresponding value for an :class:`.Array` with
            the :class:`Type` as its element.
        """

        if array_size is not None:
            return [cls.unpack(buf, ctx=ctx) for x in range(array_size)]

        array = []
        while True:
            try:
                elem = cls.unpack(buf, ctx=ctx)

            except:
                return array

            array.append(elem)

    @classmethod
    def _array_num_elements(cls, value, *, ctx):
        """Gets the number of elements for an :class:`.Array` with the :class:`Type` as its element.

        This method is only called when the :class:`.Array` is prefixed
        by a :class:`Type` or has a size of ``None``, meaning it should
        read until the end of a :class:`.Packet`, since in all other cases
        the number of elements is predetermined.

        Parameters
        ----------
        value
            The value to get the number of elements of.
        ctx : :class:`Type.Context`
            The context for the :class:`Type`.

        Returns
        -------
        :class:`int`
            The corresponding number of elements for ``value``.
        """

        return len(value)

    @classmethod
    def _array_ensure_size(cls, value, array_size, *, ctx):
        """Ensures the value of an :class:`.Array` with the :class:`Type` as its element is the correct size.

        Parameters
        ----------
        value
            The value to ensure is the correct size.
        array_size : :class:`int`
            The number of elements that the value should hold.
        ctx : :class:`Type.Context`
            The context for the :class:`Type`.

        Returns
        -------
        any
            The value of the :class:`.Array` which has ``array_size`` elements.
        """

        value_len = len(value)

        if value_len < array_size:
            return value + cls._array_default(array_size - value_len, ctx=ctx)

        if value_len > array_size:
            return value[:array_size]

        return value

    @classmethod
    def _array_pack(cls, value, array_size, *, ctx):
        """Packs the value of an :class:`.Array` with the :class:`Type` as its element.

        Parameters
        ----------
        value
            The value of the :class:`.Array`.
        array_size : :class:`int`
            The number of elements in the :class:`.Array`.
        ctx : :class:`Type.Context`
            The context for the :class:`Type`.

        Returns
        -------
        :class:`bytes`
            The corresponding raw data of the :class:`.Array`.

            This only includes the *body* of the :class:`.Array`,
            not length prefixes or anything of that sort.
        """

        return b"".join(cls.pack(x, ctx=ctx) for x in value)

    @classmethod
    def _array_transform_value(cls, value):
        """Transforms the value of an :class:`.Array` field with the :class:`Type` as its element.

        Called when the descriptor form of an :class:`.Array` has its value set.

        Parameters
        ----------
        value
            The original value.

        Returns
        -------
        any
            The transformed value.

            This transformed value will be the one that gets set.
        """

        return value

    # TODO: When Python 3.7 support is dropped, make 'name' and 'bases' positional-only.
    @classmethod
    @util.cache(force_hashable=False)
    def make_type(cls, name, bases=None, **namespace):
        """Utility for generating new types.

        The generated type's :attr:`__module__` attribute is
        set to be the same as the origin type's. This is done to
        get around an issue where generated types would have
        their :attr:`__module__` attribute be ``"abc"`` because
        :class:`Type` inherits from :class:`abc.ABC`.

        This method is cached so a new type is only made if it
        hasn't been made before.

        Parameters
        ----------
        name : :class:`str`
            The generated type's name.
        bases : :class:`tuple`
            The generated type's base classes. If unspecified, the
            origin type is the sole base class.
        **namespace
            The attributes and corresponding values of the generated
            type.

        Returns
        -------
        subclass of :class:`Type`
            The generated type.
        """

        if bases is None:
            bases = (cls,)

        namespace.setdefault("__module__", cls.__module__)

        return type(name, bases, namespace)

    @classmethod
    def _call(cls):
        # Called when the type's constructor is called.
        #
        # The arguments passed to the constructor get forwarded
        # to this method. typically overridden to enable
        # generating new types.

        raise NotImplementedError
