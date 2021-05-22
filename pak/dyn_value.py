"""Code for transforming certain values into dynamic values."""

import abc

from . import util

class DynamicValue(abc.ABC):
    """A definition of how to dynamically get a vlue from another.

    :class:`Types <~.Type>` and :class:`Packets <~.Packet>`
    have certain attributes whose values can be transformed
    into something callable-*ish*. :class:`DynamicValue` is
    the mechanism behind that transformation.

    To enroll a certain type into the :class:`DynamicValue`
    machinery, make a subclass of :class:`DynamicValue`,
    setting the :attr:`_type` attribute to the type in question.

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

    .. testoutput::

        True
        olleH

    Parameters
    ----------
    initial_value
        The initial value for the :class:`DynamicValue`.

    Returns
    -------
    any
        If the type of ``inital_value`` is someting for
        :class:`DynamicValue` to deal with, then an instance
        of the appropriate subclass will be returned.

        Otherwise, ``initial_value`` is returned.

    Attributes
    ----------
    _type : :class:`type`
        The type for the :class:`DynamicValue` to deal with.
    """

    _type = None

    def __new__(cls, initial_value):
        for subclass in util.subclasses(DynamicValue):
            if subclass._type is not None and isinstance(initial_value, subclass._type):
                return subclass(initial_value)

        return initial_value

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # Reset __new__ to a conventional state.
        if cls.__new__ is DynamicValue.__new__:
            cls.__new__ = lambda cls, *args, **kwargs: object.__new__(cls)

    @abc.abstractmethod
    def get(self, *, ctx=None):
        """Gets the dynamic value.

        Parameters
        ----------
        ctx : :class:`PacketContext` or :class:`TypeContext`
            The context for the dynamic value.

        Returns
        -------
        any
            The dynamic value.
        """

        raise NotImplementedError
