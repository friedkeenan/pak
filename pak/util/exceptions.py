"""Custom exceptions."""

__all__ = [
    "BufferOutOfDataError",
]

class BufferOutOfDataError(Exception):
    """May be raised when a buffer runs out of data.

    Warnings
    --------
    Do not rely on :class:`Types <.Type>` raising this when their buffer
    runs out of data. This is only used for some :class:`Types <.Type>`
    to have a more specific error.
    """
