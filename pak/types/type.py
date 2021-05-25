"""Base code for types."""

import abc
import inspect
import copy
import functools

from .. import util
from ..dyn_value import DynamicValue

__all__ = [
    "TypeContext",
    "Type",
]

class TypeContext:
    """The context for a :class:`Type`.

    Parameters
    ----------
    packet : :class:`~.Packet`
        The packet instance that's being marshaled.
    ctx : :class:`~.PacketContext`
        The context for the packet that's being marshaled.

        Getting attributes that are not directly in the
        :class:`TypeContext` will be gotten from the
        packet context.

    Attributes
    ----------
    packet : :class:`~.Packet` or ``None``
        The packet instance that's being marshaled.
    packet_ctx : :class:`~.PacketContext` or ``None``
        The context for the packet that's being marshaled.

        Getting attributes that are not directly in the
        :class:`~TypeContext` will be gotten from this.
    """

    def __init__(self, packet=None, *, ctx=None):
        self.packet     = packet
        self.packet_ctx = ctx

    def __getattr__(self, attr):
        return getattr(self.packet_ctx, attr)

class Type(abc.ABC):
    r"""A definition of how to marshal raw data to and from values.

    Typically used for the types of :class:`~.Packet` fields.

    When :class:`Types <Type>` are called, their :meth:`_call`
    :class:`classmethod` gets called, returning a new :class:`Type`.

    :class:`~.Array` types can be constructed using indexing syntax,
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
    to :class:`~.Array`.

    Parameters
    ----------
    typelike
        The typelike object to convert to a :class:`Type`.

    Raises
    ------
    :exc:`TypeError`
        If ``typelike`` can't be converted to a :class:`Type`.
    """

    _typelikes = {}

    _size    = None
    _default = None

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

    @staticmethod
    def prepare_types(func):
        """A decorator that converts arguments annotated with :class:`Type` to a :class:`Type`."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            args_annotations, kwargs_annotations = util.arg_annotations(func, *args, **kwargs)

            new_args = [
                Type(x) if y is Type
                else x

                for x, y in args_annotations
            ]

            new_kwargs = {}
            for name, (value, annotation) in kwargs_annotations.items():
                if annotation is Type:
                    value = Type(value)

                new_kwargs[name] = value

            return func(*new_args, **new_kwargs)

        return wrapper

    @classmethod
    def __class_getitem__(cls, index):
        """Gets an :class:`.Array` of the :class:`Type`.

        Parameters
        ----------
        index : :class:`int` or subclass of :class:`Type` or :class:`str` or :class:`function` or ``None``
            The ``size`` argument passed to :class:`~.Array`.

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

        cls._size    = DynamicValue(inspect.getattr_static(cls, "_size"))
        cls._default = DynamicValue(inspect.getattr_static(cls, "_default"))

        # Set __new__ to _call's underlying function.
        # We don't just override __new__ instead of
        # _call so that it's more clear that calling
        # a Type is separate from actually initializing
        # an instance of Type.
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

    @classmethod
    def size(cls, *, ctx=None):
        """Gets the size of the :class:`Type` when packed.

        If the :attr:`_size` attribute is a :class:`classmethod`,
        then it should look like this::

            @classmethod
            def _size(cls, *, ctx=None):
                return my_size

        The return value of the :class:`classmethod` wil be returned from
        this method.

        Else, if the :attr:`_size` attribute is a :class:`DynamicValue`,
        which it is automatically transformed into on class construction
        if applicable, the the dynamic value of that is returned.

        Otherwise, if the :attr:`_size` attribute is any value
        other than ``None``, that value will be returned.

        Parameters
        ----------
        ctx : :class:`TypeContext`
            The context for the :class:`Type`

        Returns
        -------
        :class:`int`
            The size of the :class:`Type` when packed.

        Raises
        ------
        :exc:`TypeError`
            If the :class:`Type` has no size.
        """

        if cls._size is None:
            raise TypeError(f"{cls.__name__} has no size")

        if inspect.ismethod(cls._size):
            return cls._size(ctx=ctx)

        if isinstance(cls._size, DynamicValue):
            return cls._size.get(ctx=ctx)

        return cls._size

    @classmethod
    def default(cls, *, ctx=None):
        """Gets the default value of the :class:`Type`.

        If the :attr:`_default` attribute is a :class:`classmethod`,
        then it should look like this::

            @classmethod
            def _default(cls, *, ctx=None):
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
        ctx : :class:`TypeContext`
            The context for the type.

        Returns
        -------
        any
            The default value.

        Raises
        ------
        :exc:`NotImplementedError`
            If the :attr:`_default` attribute is ``None``.
        """

        if cls._default is None:
            raise NotImplementedError(f"No default has been set for {cls.__name}")

        if inspect.ismethod(cls._default):
            return cls._default(ctx=ctx)

        if isinstance(cls._default, DynamicValue):
            return cls._default.get(ctx=ctx)

        # Deepcopy because the default could be mutable.
        return copy.deepcopy(cls._default)

    @classmethod
    def unpack(cls, buf, *, ctx=None):
        """Unpacks raw data into its corresponding value.

        Warnings
        --------
        Do **not** override this method. Instead override
        :meth:`_unpack`.

        Parameters
        ----------
        buf : file object or :class:`bytes` or :class:`bytearray`
            The buffer containing the raw data.
        ctx : :class:`TypeContext`
            The context for the type.

        Returns
        -------
        any
            The corresponding value of the buffer.
        """

        buf = util.file_object(buf)

        return cls._unpack(buf, ctx=ctx)

    @classmethod
    def pack(cls, value, *, ctx=None):
        """Packs a value into its corresponding raw data.

        Warnings
        --------
        Do **not** override this method. Instead override
        :meth:`_pack`.

        Parameters
        ----------
        value
            The value to pack.
        ctx : :class:`TypeContext`
            The context for the type.

        Returns
        -------
        :class:`bytes`
            The corresponding raw data.
        """

        return cls._pack(value, ctx=ctx)

    @classmethod
    @abc.abstractmethod
    def _unpack(cls, buf, *, ctx=None):
        """Unpacks raw data into its corresponding value.

        To be overridden by subclasses.

        Warnings
        --------
        Do not use this method directly, **always** use
        :meth:`unpack` instead.

        Parameters
        ----------
        buf : file object
            The buffer containing the raw data.
        ctx : :class:`TypeContext`
            The context for the type.

        Returns
        -------
        any
            The corresponding value from the buffer.
        """

        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _pack(cls, value, *, ctx=None):
        """Packs a value into its corresponding raw data.

        To be overridden by subclasses.

        Warnings
        --------
        Do not use this method directly, **always** use
        :meth:`pack` instead.

        Parameters
        ----------
        value
            The value to pack.
        ctx : :class:`TypeContext`
            The context for the type.

        Returns
        -------
        :class:`bytes`
            The corresponding raw data.
        """

        raise NotImplementedError

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

        namespace["__module__"] = cls.__module__

        return type(name, bases, namespace)

    @classmethod
    def _call(cls):
        # Called when the type's constructor is called.
        #
        # The arguments passed to the constructor get forwarded
        # to this method. typically overridden to enable
        # generating new types.

        raise NotImplementedError
