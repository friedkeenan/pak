r"""Tools for handling :class:`~.Packet`\s."""

import inspect

__all__ = [
    "packet_listener",
    "PacketHandler",
]

def packet_listener(*packet_types, **flags):
    r"""A decorator for :class:`~.Packet` listeners.

    See Also
    --------
    :meth:`PacketHandler.register_packet_listener`

    Parameters
    ----------
    *packet_types : subclass of :class:`~.Packet`
        The :class:`~.Packet`\s to listen for.
    **flags
        The flags which must match for the listener to be returned by
        :meth:`PacketHandler.listeners_for_packet`.

    Examples
    --------
    >>> import pak
    >>> class Example(pak.PacketHandler):
    ...     @pak.packet_listener(pak.Packet)
    ...     def listener_example(self, packet):
    ...         # Do things with 'packet' here.
    ...         pass
    ...
    >>> ex = Example()
    >>> ex.is_listener_registered(ex.listener_example)
    True
    """

    # Mark the decorated listener with the passed in arguments
    # to be later consumed on PacketHandler construction.
    def decorator(listener):
        listener._packet_listener_data = (packet_types, flags)

        return listener

    return decorator

class PacketHandler:
    r"""An object which handles :class:`Packet`\s by dispatching them to listener
    methods or functions.

    On construction, methods decorated with :func:`packet_listener` are passed
    to :meth:`register_packet_listener`.
    """

    def __init__(self):
        self._packet_listeners = {}

        # Register all the packet listeners decorated with 'packet_listener',
        # which have the '_packet_listener_data' attribute.
        for _, attr in inspect.getmembers(self, lambda x: hasattr(x, "_packet_listener_data")):
            packet_types, flags = attr._packet_listener_data

            self.register_packet_listener(attr, *packet_types, **flags)

    def is_listener_registered(self, listener):
        """Gets whether a :class:`~.Packet` listener is registered.

        Parameters
        ----------
        listener
            The :class`~.Packet` listener possibly passed to
            :meth:`register_packet_listener`.

        Returns
        -------
        :class:`bool`
            Whether `listener` is a registered :class:`~.Packet` listener.
        """

        return listener in self._packet_listeners

    def register_packet_listener(self, listener, *packet_types, **flags):
        r"""Registers a :class:`~.Packet` listener.

        See Also
        --------
        :meth:`listeners_for_packet`

        Parameters
        ----------
        listener
            The :class:`~.Packet` listener to register.
        *packet_types : subclass of :class:`~.Packet`
            The :class:`~.Packet`\s to listen for.
        **flags
            The flags which must match for the listener to be returned by
            :meth:`PacketHandler.listeners_for_packet`.

        Raises
        ------
        :exc:`TypeError`
            If ``*packet_types`` is empty.
        :exc:`ValueError`
            If ``listener`` is already registered.

        Examples
        --------
        >>> import pak
        >>> def listener_example(packet):
        ...     # Do things with 'packet' here.
        ...     pass
        ...
        >>> handler = pak.PacketHandler()
        >>> handler.register_packet_listener(listener_example, pak.Packet)
        >>> handler.is_listener_registered(listener_example)
        True
        """

        if len(packet_types) == 0:
            raise TypeError("Must pass at least one packet type")

        if self.is_listener_registered(listener):
            raise ValueError(
                f"'{repr(listener)}'' is already a registered packet listener"
            )

        self._packet_listeners[listener] = (packet_types, flags)

    def unregsiter_packet_listener(self, listener):
        """Unregisters a :class:`~.Packet` listener.

        Parameters
        ----------
        listener
            The :class:`~.Packet` listener passed to :meth:`register_packet_listener`.
        """

        self._packet_listeners.pop(listener)

    def listeners_for_packet(self, packet, **flags):
        """Gets the listeners for a certain :class:`~.Packet`.

        It is the caller's responsibility to send the :class:`~.Packet`
        to the returned listeners.

        Parameters
        ----------
        packet : :class:`~.Packet`
            The :class:`~.Packet` to get listeners for.
        **flags
            The flags which must match the flags a listener was registered
            with for the listener to be returned.

        Returns
        -------
        :class:`list`
            The list of listeners for ``packet``.

        Examples
        --------
        >>> import pak
        >>> class Example(pak.PacketHandler):
        ...     @pak.packet_listener(pak.Packet)
        ...     def listener_example(self, packet):
        ...         # Do things with 'packet' here.
        ...         pass
        ...     def __repr__(self):
        ...         return "Example()"
        ...
        >>> ex = Example()
        >>> ex.listeners_for_packet(pak.Packet())
        [<bound method Example.listener_example of Example()>]
        """

        return [
            listener

            for listener, (packet_types, listener_flags) in self._packet_listeners.items()

            if isinstance(packet, packet_types) and listener_flags == flags
        ]
