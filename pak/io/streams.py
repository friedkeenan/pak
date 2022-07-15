"""Asynchronous data streams."""

import asyncio

from .. import util

__all__ = [
    "ByteStreamReader",
]

class ByteStreamReader:
    """An :class:`asyncio.StreamReader` which reads from predetermined data.

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

    async def readuntil(self, separator=b"\n"):
        """Reads until ``separator`` is found.

        Parameters
        ----------
        separator : :class:`bytes`
            The string of bytes to find.

        Returns
        -------
        :class:`bytes`
            The data read from the stream.

            ``separator`` will be included in the data.

        Raises
        ------
        :exc:`ValueError`
            If ``separator`` doesn't contain at least one byte.
        :exc:`asyncio.IncompleteReadError`
            If ``separator`` cannot be found.

            The ``partial`` attribute will contain the
            partially read data, potentially including
            part of ``separator``.
        """

        if len(separator) == 0:
            raise ValueError("Separator must contain at least one byte")

        pos = self._buffer.find(separator)
        if pos < 0:
            raise asyncio.IncompleteReadError(partial=await self.read(), expected=None)

        return await self.readexactly(pos + len(separator))

    def at_eof(self):
        """Gets whether the stream has ended.

        Returns
        -------
        :class:`bool`
            Whether the stream has ended.
        """

        return len(self._buffer) == 0
