"""Code for transforming certain values into dynamic values."""

import abc
from contextlib import contextmanager

from . import util

__all__ = [
    "DynamicValue",
]

class DynamicValue(abc.ABC):
    r"""A definition of how to dynamically get one value from another.

    :class:`.Type`\s and :class:`.Packet`\s have certain attributes
    whose values can be transformed into something callable-*ish*.
    :class:`DynamicValue` is the mechanism behind that transformation.

    To enroll a certain type into the :class:`DynamicValue`
    machinery, make a subclass of :class:`DynamicValue`,
    setting the :attr:`_type` attribute to the type in question.
    Doing so will "enable" the subclass on class initialization.
    This can be overridden by setting the :attr:`_enabled` attribute
    explicitly.

    Alternatively, there are also the :meth:`enable` and :meth:`disable`
    methods, and the :meth:`context` method for context management.

    For instance, to enroll :class:`str` into the machinery:

    .. testcode::

        import pak

        class StringDynamicValue(pak.DynamicValue):
            _type = str

            # The initial value is passed to
            # the constructor.
            def __init__(self, string):
                self.string = string

            # The dynamic value is returned
            # from the "get" method.
            #
            # Here we return the reversed string.
            def get(self, *, ctx=None):
                return self.string[::-1]

        # This will lead to the following behavior:
        v = pak.DynamicValue("Hello")
        print(isinstance(v, StringDynamicValue))
        print(v.get())

        StringDynamicValue.disable()
        print(pak.DynamicValue("Hello"))

    .. testoutput::

        True
        olleH
        Hello

    Parameters
    ----------
    initial_value
        The initial value for the :class:`DynamicValue`.

    Returns
    -------
    any
        If the type of ``inital_value`` is something for
        :class:`DynamicValue` to deal with, then an instance
        of the appropriate subclass will be returned.

        Otherwise, ``initial_value`` is returned.

    Attributes
    ----------
    _type : :class:`type`
        The type for the :class:`DynamicValue` to deal with.
    _enabled : :class:`bool`
        Whether the :class:`DynamicValue` is enabled.
    """

    _type    = None
    _enabled = None

    def __new__(cls, initial_value):
        for subclass in util.subclasses(DynamicValue):
            if subclass._enabled and isinstance(initial_value, subclass._type):
                return subclass(initial_value)

        return initial_value

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if cls._enabled is None:
            # NOTE: Calling 'enable' sets the '_enabled' attribute,
            # which may make this problematic with inheritance.
            # Presently however we do not care about this potential issue.
            cls.enable()

        # Reset '__new__' to a conventional state.
        if cls.__new__ is DynamicValue.__new__:
            cls.__new__ = lambda cls, *args, **kwargs: object.__new__(cls)

    @classmethod
    def enable(cls):
        """Enables the class to be used in the :class:`DynamicValue` machinery."""

        cls._enabled = True

    @classmethod
    def disable(cls):
        """Disables the class to be used in the :class:`DynamicValue` machinery."""

        cls._enabled = False

    @classmethod
    @contextmanager
    def context(cls):
        """Temporarily enables then disables the class.

        Examples
        --------
        >>> import pak
        >>> class StringToIntDynamicValue(pak.DynamicValue):
        ...     _type = str
        ...     def __init__(self, string):
        ...         self.string = string
        ...     def get(self, *, ctx=None):
        ...         return int(self.string)
        ...
        >>> with StringToIntDynamicValue.context():
        ...     print(isinstance(pak.DynamicValue("1"), StringToIntDynamicValue))
        ...
        True
        >>> pak.DynamicValue("1")
        '1'
        """

        try:
            cls.enable()

            yield
        finally:
            cls.disable()

    @abc.abstractmethod
    def get(self, *, ctx=None):
        """Gets the dynamic value.

        Parameters
        ----------
        ctx : :class:`.Packet.Context` or :class:`.Type.Context`
            The context for the dynamic value.

        Returns
        -------
        any
            The dynamic value.
        """

        raise NotImplementedError
