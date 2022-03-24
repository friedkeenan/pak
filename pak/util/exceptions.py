"""Custom exceptions."""

__all__ = [
    "BufferOutOfDataError",
]

class BufferOutOfDataError(Exception):
    r"""May be raised when a buffer runs out of data.

    Warnings
    --------
    Do not rely on :class:`~.Types`\s raising this when their buffer
    runs out of data. This is only used for some :class:`~.Type`\s
    to have a more specific error.
    """
