"""Asynchronous I/O utilities."""

import asyncio

__all__ = [
    "AsyncValueHolder",
]

class AsyncValueHolder:
    """An asynchronous value holder.

    This is essentially a wrapper around :class:`asyncio.Future` to give it
    a nicer API.
    """

    def __init__(self):
        self._future = asyncio.get_running_loop().create_future()

    async def get(self):
        """Gets the held value, waiting until a value is held.

        A value is not held until the :meth:`set` method is called.

        Returns
        -------
        any
            The held value.
        """

        await self._future

        return self._future.result()

    def set(self, value):
        """Sets the held value.

        The held value should be acquired using the :meth:`get` method.

        Parameters
        ----------
        value
            The value to hold.
        """

        self._future.set_result(value)
