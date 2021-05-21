"""Types for numbers."""

from .misc import StructType

__all__ = [
    "Bool",
    "Int8",
    "UInt8",
    "Int16",
    "UInt16",
    "Int32",
    "UInt32",
    "Int64",
    "UInt64",
    "Float32",
    "Float64",
]

class Bool(StructType):
    """A single byte truth-value."""

    _default = False
    fmt      = "?"

class Int8(StructType):
    """A signed 8-bit integer."""

    _default = 0
    fmt      = "b"

class UInt8(StructType):
    """An unsigned 8-bit integer."""
    _default = 0
    fmt      = "B"

class Int16(StructType):
    """A signed 16-bit integer."""

    _default = 0
    fmt      = "h"

class UInt16(StructType):
    """An unsigned 16-bit integer."""

    _default = 0
    fmt      = "H"

class Int32(StructType):
    """A signed 32-bit integer."""

    _default = 0
    fmt      = "i"

class UInt32(StructType):
    """An unsigned 32-bit integer."""

    _default = 0
    fmt      = "I"

class Int64(StructType):
    """A signed 64-bit integer."""

    _default = 0
    fmt      = "q"

class UInt64(StructType):
    """An unsigned 64-bit integer."""

    _default = 0
    fmt      = "Q"

class Float32(StructType):
    """A 32-bit floating point :class:`~.Type`."""

    _default = 0.0
    fmt      = "f"

class Float64(StructType):
    """A 54-bit floating point :class:`~.Type`."""

    _default = 0.0
    fmt      = "d"
