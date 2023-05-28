"""Contains :class:`io.Connection <.Connection>`."""

import abc
import asyncio

from .. import util

__all__ = [
    "Connection",
]

class Connection(abc.ABC):
    r"""A connection between two :class:`.Packet` sources.

    This class models a protocol structure that is relatively common,
    where there is a stream of incoming :class:`.Packet`\s that
    aren't expected to be any specific type of :class:`.Packet`.

    This may not model your protocol structure adequately.
    This in particular may be the case if you are not able
    to read and send data asynchronously. In such a case,
    you should not use this class.

    Parameters
    ----------
    reader : :class:`asyncio.StreamReader` or ``None``
        The stream for incoming data.
    writer : :class:`asyncio.StreamWriter` or ``None``
        The stream for outgoing data.
    ctx : :class:`.Packet.Context`
        The context for incoming and outgoing :class:`.Packet`\s.

    Attributes
    ----------
    reader : :class:`asyncio.StreamReader` or ``None``
        The stream for incoming data.
    writer : :class:`asyncio.StreamWriter` or ``None``
        The stream for outgoing data.
    ctx : :class:`.Packet.Context`
        The context for incoming and outgoing :class:`.Packet`\s.

        This should **always** be passed to :class:`.Packet`
        operations, such as :meth:`.Packet.unpack` and
        :meth:`.Packet.pack`.

    Examples
    --------
    A :class:`Connection` can be used in an ``async with`` statement, like so::

        connection = ...

        async with connection:
            ...

    This will make sure that ``connection`` is closed by the end
    of the of the ``async with`` statement.
    """

    def __init__(self, *, reader=None, writer=None, ctx):
        self.reader = reader
        self.writer = writer

        self.ctx = ctx

        self._packet_watch_info = {}

    def is_closing(self):
        """Gets whether the :class:`Connection` is closed or in the process of closing.

        Returns
        -------
        :class:`bool`
            Whether the :class:`Connection` is closed or in the process of closing.
        """

        # 'StreamReader' cannot be closed.
        return self.writer is None or self.writer.is_closing()

    def close(self):
        """Closes the :class:`Connection`.

        This method should be used along with the :meth:`wait_closed` method.
        """

        self._cancel_packet_watches()

        if self.writer is None:
            return

        self.writer.close()

    async def wait_closed(self):
        """Waits until the :class:`Connection` is closed."""

        if self.writer is None:
            return

        await self.writer.wait_closed()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        self.close()
        await self.wait_closed()

    # TODO: When Python 3.7 support is dropped, make 'packet_cls' positional-only.
    def create_packet(self, packet_cls, **fields):
        """Creates a :class:`.Packet` for the :class:`Connection`.

        The :attr:`ctx` attribute is used to create the :class:`.Packet`.

        Parameters
        ----------
        packet_cls : subclass of :class:`.Packet`
            The :class:`.Packet` to create.
        **fields
            The names and corresponding values of the
            :class:`.Packet` to create.

        Returns
        -------
        :class:`.Packet`
            The created :class:`.Packet`.
        """

        return packet_cls(**fields, ctx=self.ctx)

    async def read_data(self, size):
        """Reads incoming data out of the :attr:`reader` attribute.

        Parameters
        ----------
        size : :class:`int`
            How many bytes to read.

        Returns
        -------
        :class:`bytes` or ``None``
            The incoming data.

            If EOF is reached on the :attr:`reader` attribute and
            ``size`` bytes cannot be read, then ``None`` is returned.
        """

        try:
            return await self.reader.readexactly(size)

        except asyncio.IncompleteReadError:
            # We return 'None' instead of letting the exception
            # propagate because reaching EOF is something that
            # should be explicitly handled by the user at the
            # call site.
            return None

    @abc.abstractmethod
    async def _read_next_packet(self):
        """Reads the next incoming :class:`.Packet`.

        .. note::

            In your implementation, you do not need to ensure
            that reading is atomic.

        .. seealso::

            :meth:`read_data`

        Returns
        -------
        :class:`.Packet` or ``None``
            The next incoming :class:`.Packet`.

            If ``None``, then that means that there is no
            next :class:`.Packet` and that :meth:`continuously_read_packets`
            should end. This should be when EOF is reached
            on the :attr:`reader` attribute, which will be
            when :meth:`read_data` returns ``None``.
        """

        raise NotImplementedError

    def _dispatch_to_packet_watches(self, packet):
        # Make a copy of the items so we may modify
        # 'self._packet_watch_info' within the same loop.
        for packet_cls, packet_holder in list(self._packet_watch_info.items()):
            if isinstance(packet, packet_cls):
                packet_holder.set(packet)
                self._packet_watch_info.pop(packet_cls)

                # Don't break here since there could be other
                # packet watches that requested a more derived
                # subclass of 'packet_cls'.

    def _cancel_packet_watches(self):
        # Make a copy of the items so we may modify
        # 'self._packet_watch_info' within the same loop.
        for packet_cls, packet_holder in list(self._packet_watch_info.items()):
            packet_holder.set(None)
            self._packet_watch_info.pop(packet_cls)

    async def continuously_read_packets(self):
        r"""Continuously reads and yields all incoming :class:`.Packet`\s.

        .. note::

            This must be iterated over for :meth:`read_packet` to function.

        This will continue to yield :class:`.Packet`\s until the
        :class:`Connection` is closed or EOF is reached.

        .. warning::

            This method should **not** be called twice concurrently.

            Doing so may cause data to be read incorrectly.

        Yields
        ------
        :class:`.Packet`
            An incoming :class:`.Packet`.

        Examples
        --------
        ::

            connection = ...

            async for packet in connection.continuously_read_packets():
                ...
        """

        while not self.is_closing():
            packet = await self._read_next_packet()
            if packet is None:
                self.close()
                await self.wait_closed()

                return

            self._dispatch_to_packet_watches(packet)

            yield packet

    async def watch_for_packet(self, packet_cls):
        r"""Watches for a specific type of :class:`.Packet` from the incoming stream of :class:`.Packet`\s.

        Requires :meth:`continuously_read_packets` to be iterated over.

        Parameters
        ----------
        packet_cls : subclass of :class:`.Packet`
            The type of :class:`.Packet` to watch for.

        Returns
        -------
        :class:`.Packet` or ``None``
            The specified incoming :class:`.Packet`.

            Returns ``None`` when the :class:`Connection` is closed
            or EOF is reached.
        """

        packet_holder = self._packet_watch_info.get(packet_cls)
        if packet_holder is None:
            packet_holder                       = util.AsyncValueHolder()
            self._packet_watch_info[packet_cls] = packet_holder

        return await packet_holder.get()

    def is_watching_for_packet(self, packet_cls):
        """Gets whether a specific type of :class:`.Packet` is being watched for.

        .. seealso::

            :meth:`watch_for_packet`

        Parameters
        ----------
        packet_cls : subclass of :class:`.Packet`
            The type of :class:`.Packet` to check.

        Returns
        -------
        :class:`bool`
            Whether ``packet_cls`` is being watched for.
        """

        for watch_cls in self._packet_watch_info.keys():
            if issubclass(packet_cls, watch_cls):
                return True

        return False

    async def write_data(self, data):
        """Writes outgoing data to the :attr:`writer` attribute.

        Parameters
        ----------
        data : :class:`bytes`
            The data to write.
        """

        self.writer.write(data)
        await self.writer.drain()

    # TODO: When Python 3.7 support is dropped, make 'packet_cls' positional-only.
    async def write_packet(self, packet_cls, **fields):
        """Writes an outgoing :class:`.Packet`.

        This method uses :meth:`create_packet` to create the
        :class:`.Packet` to write. It then passes it to
        :meth:`write_packet_instance`.

        If you have an already created :class:`.Packet` you
        wish to write, then you should use :meth:`write_packet_instance`.

        Parameters
        ----------
        packet_cls : subclass of :class:`.Packet`
            The type of :class:`.Packet` to write.
        **fields
            The names and corresponding values of the
            :class:`.Packet` to write.
        """

        await self.write_packet_instance(self.create_packet(packet_cls, **fields))

    @abc.abstractmethod
    async def write_packet_instance(self, packet):
        """Writes an outgoing :class:`.Packet` instance.

        .. warning::

            In most cases, the :meth:`write_packet` method should be used instead.
            This method should only be used if you have a pre-existing :class:`.Packet`
            instance.

        .. note::

            In your implementation, writes should be atomic.

            It is thus recommended to only write data in one fell swoop.

        .. seealso::

            :meth:`write_data`

        Parameters
        ----------
        packet : :class:`.Packet`
            The :class:`.Packet` to write.
        """

        raise NotImplementedError
