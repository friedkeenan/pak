r"""Tools for handling :class:`.Packet`\s."""

import asyncio
import inspect
import types

__all__ = [
    "packet_listener",
    "most_derived_packet_listener",
    "PacketHandler",
    "AsyncPacketHandler",
]

def packet_listener(*packet_types, **flags):
    r"""A decorator for :class:`.Packet` listeners.

    .. seealso::

        :meth:`PacketHandler.register_packet_listener`

    Parameters
    ----------
    *packet_types : subclass of :class:`.Packet`
        The :class:`.Packet`\s to listen for.
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

class _most_derived_packet_listener:
    class _bound:
        def __init__(self, parent, instance):
            self.__qualname__ = parent.__qualname__

            self._listeners = parent._listeners
            self._packet_listener_data = ((parent._general_type,), parent._flags)

            # Setting this will make the '_bound' object immutable.
            self._instance  = instance

        def to_real_listener(self, packet):
            for base in type(packet).mro():
                listener = self._listeners.get(base)

                if listener is not None:
                    # Return bound method
                    return types.MethodType(listener, self._instance)

        def __setattr__(self, attr, value):
            if hasattr(self, "_instance"):
                raise TypeError(f"{repr(self)} is immutable")

            super().__setattr__(attr, value)

        def __hash__(self):
            # Use 'frozenset' to ignore the order of listeners.
            return hash((frozenset(self._listeners.items()), id(self._instance)))

        def __eq__(self, other):
            return (
                self._instance is other._instance and

                # Use 'frozenset' to ignore the order of listeners.
                frozenset(self._listeners.items()) == frozenset(self._listeners.items())
            )

        def __repr__(self):
            return f"<bound most_derived_packet_listener {self.__qualname__} of {repr(self._instance)}>"

    def __init__(self, most_general_packet_type, listeners, flags):
        self._general_type = most_general_packet_type
        self._listeners    = listeners
        self._flags        = flags

    def __set_name__(self, owner, name):
        self.__module__   = owner.__module__
        self.__qualname__ = f"{owner.__qualname__}.{name}"

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

        return self._bound(self, instance)

    def derived_listener(self, derived_packet_type, *, override=False):
        if not issubclass(derived_packet_type, self._general_type):
            raise ValueError(f"'{derived_packet_type.__qualname__}' is not a subclass of '{self._general_type.__qualname__}'")

        if not override and derived_packet_type in self._listeners:
            raise ValueError(f"most_derived_packet_listener already has a listener for {derived_packet_type.__qualname__}")

        def decorator(listener):
            new_listeners = dict(self._listeners)
            new_listeners[derived_packet_type] = listener

            return _most_derived_packet_listener(self._general_type, new_listeners, self._flags)

        return decorator

    def __repr__(self):
        return f"<most_derived_packet_listener {self.__module__}.{self.__qualname__}>"

def most_derived_packet_listener(most_general_packet_type, **flags):
    r"""A decorator for :class:`.Packet` listeners that dispatch only to the
    listener corresponding to the most derived :class:`.Packet` type.

    Parameters
    ----------
    most_general_packet_type : subclass of :class:`.Packet`
        The most general :class:`.Packet` for the listener, i.e. the
        base class for all the :class:`.Packet`\s the listener will
        handle.
    **flags
        See :meth:`PacketHandler.listeners_for_packet`.

    Examples
    --------
    >>> import pak
    >>> class GeneralPacket(pak.Packet):
    ...     pass
    ...
    >>> class DerivedPacket(GeneralPacket):
    ...     pass
    ...
    >>> class MoreDerivedPacket(DerivedPacket):
    ...     pass
    ...
    >>> class MyHandler(pak.PacketHandler):
    ...     @pak.most_derived_packet_listener(GeneralPacket)
    ...     def most_derived(self):
    ...         return "general"
    ...
    ...     @most_derived.derived_listener(DerivedPacket)
    ...     def most_derived(self):
    ...         return "derived"
    ...
    ...     @most_derived.derived_listener(MoreDerivedPacket)
    ...     def most_derived(self):
    ...         return "more derived"
    ...
    >>> handler = MyHandler()
    >>> handler.listeners_for_packet(GeneralPacket())[0]()
    'general'
    >>> handler.listeners_for_packet(DerivedPacket())[0]()
    'derived'
    >>> handler.listeners_for_packet(MoreDerivedPacket())[0]()
    'more derived'
    >>> # You can pass 'override=True' to 'derived_listener'
    >>> # to override a previously set listener.
    >>> class MyDerivedHandler(MyHandler):
    ...     @MyHandler.most_derived.derived_listener(MoreDerivedPacket, override=True)
    ...     def most_derived(self):
    ...         return "overridden more derived"
    ...
    >>> handler = MyDerivedHandler()
    >>> handler.listeners_for_packet(MoreDerivedPacket())[0]()
    'overridden more derived'
    """

    def decorator(listener):
        return _most_derived_packet_listener(most_general_packet_type, {most_general_packet_type: listener}, flags)

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
        """Gets whether a :class:`.Packet` listener is registered.

        Parameters
        ----------
        listener
            The :class:`.Packet` listener possibly passed to
            :meth:`register_packet_listener`.

        Returns
        -------
        :class:`bool`
            Whether ``listener`` is a registered :class:`.Packet` listener.
        """

        return listener in self._packet_listeners

    def register_packet_listener(self, listener, *packet_types, **flags):
        r"""Registers a :class:`.Packet` listener.

        .. seealso::

            :meth:`listeners_for_packet`

        Parameters
        ----------
        listener
            The :class:`.Packet` listener to register.
        *packet_types : subclass of :class:`.Packet`
            The :class:`.Packet`\s to listen for.
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
        """Unregisters a :class:`.Packet` listener.

        Parameters
        ----------
        listener
            The :class:`.Packet` listener passed to :meth:`register_packet_listener`.
        """

        self._packet_listeners.pop(listener)

    def _to_real_listener(self, listener, packet):
        method = getattr(listener, "to_real_listener", None)
        if method is None:
            return listener

        return method(packet)

    def listeners_for_packet(self, packet, **flags):
        """Gets the listeners for a certain :class:`.Packet`.

        It is the caller's responsibility to send the :class:`.Packet`
        to the returned listeners.

        If a :class:`.Packet` listener has a ``to_real_listener`` attribute,
        then that attribute will be called with the ``packet`` parameter to
        get the real :class:`.Packet` listener to be returned.

        Parameters
        ----------
        packet : :class:`.Packet`
            The :class:`.Packet` to get listeners for.
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
            self._to_real_listener(listener, packet)

            for listener, (packet_types, listener_flags) in self._packet_listeners.items()

            if isinstance(packet, packet_types) and listener_flags == flags
        ]

class AsyncPacketHandler(PacketHandler):
    r"""A :class:`PacketHandler` that handles :class:`Packet`\s asynchronously.

    This class doesn't really have different semantics from :class:`PacketHandler`,
    but it has extra facilities for asynchronously handling :class:`.Packet`\s.
    """

    class _TaskGroup:
        def __init__(self, handler, listen_sequentially):
            self.handler             = handler
            self.listen_sequentially = listen_sequentially

            # If we're listening sequentially, use our own
            # list of tasks to await separately from the
            # rest of the handler's tasks.
            #
            # This avoids an issue where if a listener task
            # itself listens sequentially to a packet, the
            # program will lock up because when leaving the
            # context manager, it will try to await its own
            # parent task.
            if listen_sequentially:
                self.listener_tasks = []
            else:
                self.listener_tasks = handler._listener_tasks

        def create_task(self, coroutine):
            if self.listen_sequentially:
                task = asyncio.create_task(coroutine)
                self.listener_tasks.append(task)

                return task

            async def coroutine_wrapper():
                try:
                    return await coroutine

                finally:
                    # 'wrapper_task' is defined later, and has to be
                    # since it's the task for this coroutine function.
                    self.listener_tasks.remove(wrapper_task)

            wrapper_task = asyncio.create_task(coroutine_wrapper())
            self.listener_tasks.append(wrapper_task)

            return wrapper_task

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, exc_tb):
            if self.listen_sequentially:
                await asyncio.gather(*self.listener_tasks)

    def __init__(self):
        self._listener_tasks = []

        super().__init__()

    async def end_listener_tasks(self, *, timeout=1):
        """Ends any outstanding listener tasks created with :meth:`listener_task_group`.

        Parameters
        ----------
        timeout : :class:`int` or :class:`float` or ``None``
            How long to wait before canceling outstanding listener tasks.

            Passed to :func:`asyncio.wait_for`.
        """

        try:
            await asyncio.wait_for(asyncio.gather(*self._listener_tasks), timeout)
        except asyncio.TimeoutError:
            # If the timeout is reached, then the gathered
            # tasks are also canceled.
            pass

    def listener_task_group(self, *, listen_sequentially):
        """Creates an asynchronous context manager in which listener tasks should be created.

        The manager has a ``create_task`` method that takes a coroutine, like so::

            handler = pak.AsyncPacketHandler()
            packet  = ...

            async with handler.listener_task_group(listen_sequentially=False) as group:
                for listener in handler.listeners_for_packet(packet):
                    group.create_task(packet)

            await handler.end_listener_tasks()

        .. note::

            This interface is similar to the :class:`asyncio.TaskGroup` class in
            Python 3.11+.

        .. warning::

            The :meth:`end_listener_tasks` method should be called
            when **all** listening should end.

        Parameters
        ----------
        listen_sequentially : :class:`bool`
            Whether the listeners should be called sequentially.

            If ``True``, listeners responding to the same :class:`.Packet`
            will still be run asynchronously, however they will all be
            awaited before listening to another :class:`.Packet`.

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
        ...
        ...     @pak.packet_listener(pak.Packet)
        ...     async def fast_listener(self, packet):
        ...         print("fast_listener")
        ...
        >>> async def main():
        ...     handler = ExampleHandler()
        ...     packet  = pak.Packet()
        ...     async with handler.listener_task_group(listen_sequentially=False) as group:
        ...         for listener in handler.listeners_for_packet(packet):
        ...             group.create_task(listener(packet))
        ...
        ...     await handler.end_listener_tasks(timeout=2)
        ...
        >>> asyncio.run(main())
        fast_listener
        slow_listener
        """

        # NOTE: In the above docstring, the example sleeping for 1 second may
        # become problematic if it becomes more common throughout our tests.

        return self._TaskGroup(self, listen_sequentially)
