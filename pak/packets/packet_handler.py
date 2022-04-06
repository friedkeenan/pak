r"""Tools for handling :class:`~.Packet`\s."""

import asyncio
import inspect
from contextlib import asynccontextmanager

__all__ = [
    "packet_listener",
    "PacketHandler",
    "AsyncPacketHandler",
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
        >>> class MyPacket(pak.Packet):
        ...     pass
        ...
        >>> class Example(pak.PacketHandler):
        ...     @pak.packet_listener(MyPacket)
        ...     def listener_example(self, packet):
        ...         # Do things with 'packet' here.
        ...         pass
        ...     def __repr__(self):
        ...         return "Example()"
        ...
        >>> ex = Example()
        >>> ex.listeners_for_packet(MyPacket())
        [<bound method Example.listener_example of Example()>]
        """

        return [
            listener

            for listener, (packet_types, listener_flags) in self._packet_listeners.items()

            if isinstance(packet, packet_types) and listener_flags == flags
        ]

class AsyncPacketHandler(PacketHandler):
    def __init__(self):
        self._listener_tasks = []

        super().__init__()

    def register_packet_listener(self, listener, *packet_types, **flags):
        r"""Registers an asynchronous :class:`~.Packet` listener.

        See :meth:`PacketHandler.register_packet_listener` for more details.

        Parameters
        ----------
        listener : coroutine function
            The asynchronous :class:`~.Packet` listener.
        *packet_types : subclass of :class:`~.Packet`
            The :class:`~.Packet`\s to listen for.
        **flags
            The flags which must match for the listener to be returned by
            :meth:`PacketHandler.listeners_for_packet`.

        Raises
        ------
        :exc:`TypeError`
            If ``listener`` is not a coroutine function.
        """

        if not inspect.iscoroutinefunction(listener):
            raise TypeError(
                f"Function {listener.__qualname__} cannot be an async packet listener because it is not a coroutine function"
            )

        super().register_packet_listener(listener, *packet_types, **flags)

    def create_listener_task(self, coroutine):
        """Creates an asynchronous task for a :class:`~.Packet` listener.

        This method should be called when creating tasks for :class:`~.Packet`
        listeners, and :meth:`end_listener_tasks` called when **all** listening
        should end.

        Tasks should only be created in a :meth:`listener_task_context` managed
        context.

        Parameters
        ----------
        coroutine : coroutine object
            The coroutine to create the task for.

        Returns
        -------
        :class:`asyncio.Task`
            The created task.
        """

        async def coroutine_wrapper():
            try:
                await coroutine

            finally:
                # 'wrapper_task' is defined later, and has to be
                # since it's the task for this coroutine function.
                self._listener_tasks.remove(wrapper_task)

        wrapper_task = asyncio.create_task(coroutine_wrapper())
        self._listener_tasks.append(wrapper_task)

        return wrapper_task

    async def end_listener_tasks(self, *, timeout=1):
        """Ends any outstanding listener tasks created with :meth:`create_listener_task`.

        Parameters
        ----------
        timeout : :class:`int` or :class:`float` or ``None``
            How long to wait before canceling outstanding listener tasks.

            Passed to :func:`asyncio.wait_for`.
        """

        try:
            await asyncio.wait_for(asyncio.gather(*self._listener_tasks), timeout)
        except asyncio.TimeoutError:
            for task in self._listener_tasks:
                task.cancel()

    @asynccontextmanager
    async def listener_task_context(self, *, listen_sequentially):
        """A context manager in which listener tasks should be created.

        Parameters
        ----------
        listen_sequentially : :class:`bool`
            Whether the listeners should be called sequentially.

            If ``True``, listeners responding to the same :class:`~.Packet`
            will still be run asynchronously, however they will all be
            awaited before listening to another :class:`~.Packet`.

            Also when ``True``, the tasks are never canceled.

        Examples
        --------
        >>> import pak
        >>> import asyncio
        >>> class ExampleHandler(pak.AsyncPacketHandler):
        ...     @pak.packet_listener(pak.Packet)
        ...     async def slow_listener(self, packet):
        ...         await asyncio.sleep(1)
        ...         print("slow_listener")
        ...     @pak.packet_listener(pak.Packet)
        ...     async def fast_listener(self, packet):
        ...         print("fast_listener")
        ...
        >>> async def main():
        ...     handler = ExampleHandler()
        ...     packet  = pak.Packet()
        ...     async with handler.listener_task_context(listen_sequentially=False):
        ...         for listener in handler.listeners_for_packet(packet):
        ...             await listener(packet)
        ...
        >>> asyncio.run(main())
        fast_listener
        slow_listener
        """

        # NOTE: In the above docstring, the example sleeping for 1 second may
        # become problematic if it becomes more common throughout our tests.

        try:
            yield
        finally:
            if listen_sequentially:
                # Awaiting all tasks will clear '_listener_tasks'.
                await asyncio.gather(*self._listener_tasks)
