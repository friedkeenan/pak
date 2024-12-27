"""Asynchronous data streams."""

import asyncio

from .. import util

__all__ = [
    "ByteStreamReader",
    "ByteStreamWriter",
]

class ByteStreamReader:
    """An :class:`asyncio.StreamReader` which reads from predetermined data.

    .. note::

        While this technically does not inherit from
        :class:`asyncio.StreamReader`, it has the same
        API and semantics. Thus it is perfectly usable
        for e.g. :class:`io.Connection <.Connection>`.

    Parameters
    ----------
    data : bytes-like
        The data to read from.
    """

    def __init__(self, data=b""):
        self._buffer = bytearray(data)

    async def read(self, n=-1):
        """Reads up to ``n`` bytes.

        Parameters
        ----------
        n : :class:`int`
            The number of bytes to read.

            If ``-1``, then read until EOF.

        Returns
        -------
        :class:`bytes`
            The data read from the stream.
        """

        await util.yield_exec()

        if n < 0:
            n = len(self._buffer)

        extracted_data = self._buffer[:n]
        self._buffer   = self._buffer[n:]

        return bytes(extracted_data)

    async def readline(self):
        """Reads until the next newline.

        If EOF is reached before the next newline,
        then partial data is returned.

        Returns
        -------
        :class:`bytes`
            The data read from the stream.

            The newline will be included in the data.
        """

        try:
            return await self.readuntil(b"\n")

        except asyncio.IncompleteReadError as e:
            return e.partial

    async def readexactly(self, n):
        """Reads exactly ``n`` bytes.

        Parameters
        ----------
        n : :class:`int`
            The exact number of bytes to read.

        Returns
        -------
        :class:`bytes`
            The data read from the stream.

        Raises
        ------
        :exc:`asyncio.IncompleteReadError`
            If ``n`` bytes cannot be read.

            The ``partial`` attribute will contain the
            partially read data.
        """

        if n > len(self._buffer):
            raise asyncio.IncompleteReadError(partial=await self.read(), expected=n)

        return await self.read(n)

    def _find_separator_end(self, separator):
        # NOTE: Support for a tuple of multiple
        # separators was added in Python 3.13.

        if not isinstance(separator, tuple):
            separator = [separator]

        match_end = None
        for to_find in separator:
            if len(to_find) <= 0:
                raise ValueError("Separator must contain at least one byte")

            pos = self._buffer.find(to_find)
            if pos >= 0:
                possible_end = pos + len(to_find)

                if match_end is None:
                    match_end = possible_end
                else:
                    match_end = min(match_end, possible_end)

        # NOTE: This will return 'None' instead of '-1'
        # to signify that we did not find any separators.
        return match_end

    async def readuntil(self, separator=b"\n"):
        """Reads until a separator is found.

        Parameters
        ----------
        separator : :class:`bytes` or :class:`tuple` of :class:`bytes`
            If :class:`bytes`, then the separator to read until.

            If a :class:`tuple`, then the collection of
            possible separators to read until. The separator
            which results in the least amount of data
            being read will be the one utilized.

        Returns
        -------
        :class:`bytes`
            The data read from the stream.

            The appropriate separator will be included in the data.

        Raises
        ------
        :exc:`ValueError`
            If the separators don't all contain at least one byte.
        :exc:`asyncio.IncompleteReadError`
            If no separator can be found.

            The ``partial`` attribute will contain the
            partially read data, potentially including
            part of a separator.
        """

        pos = self._find_separator_end(separator)
        if pos is None:
            raise asyncio.IncompleteReadError(partial=await self.read(), expected=None)

        return await self.readexactly(pos)

    def at_eof(self):
        """Gets whether the stream has ended.

        Returns
        -------
        :class:`bool`
            Whether the stream has ended.
        """

        return len(self._buffer) == 0

class ByteStreamWriter:
    """An :class:`asyncio.StreamWriter` which writes to an internal buffer.

    .. note::

        While this technically does not inherit from
        :class:`asyncio.StreamWriter`, it has the same
        API and semantics. Thus it is perfectly usable
        for e.g. :class:`io.Connection <.Connection>`.
    """

    def __init__(self):
        self._buffer = bytearray()

        self._close_event = asyncio.Event()

    @property
    def written_data(self):
        """The data that has been written.

        Returns
        -------
        :class:`bytes`
        """

        return bytes(self._buffer)

    def write(self, data):
        """Writes data to the internal buffer.

        This method should be used along with the :meth:`drain` method.

        Parameters
        ----------
        data : bytes-like
            The data to write.
        """

        self._buffer.extend(data)

    def writelines(self, data):
        """Writes an iterable of bytes to the internal buffer.

        This method should be used along with the :meth:`drain` method.

        Parameters
        ----------
        data : iterable of bytes-like
            The iterable of bytes to write.
        """

        self.write(b"".join(data))

    async def drain(self):
        """Waits until it is appropriate to resume writing to the :class:`ByteStreamWriter`."""

        await util.yield_exec()

    def close(self):
        """Closes the :class:`ByteStreamWriter`.

        This method should be used along with the :meth:`wait_closed` method.
        """

        self._close_event.set()

    def is_closing(self):
        """Gets whether the :class:`ByteStreamWriter` is closed or in the process of closing.

        Returns
        -------
        :class:`bool`
            Whether the :class:`ByteStreamWriter` is closed or in the process of closing.
        """

        return self._close_event.is_set()

    async def wait_closed(self):
        """Waits until the :class:`ByteStreamWriter` is closed."""

        await self._close_event.wait()
