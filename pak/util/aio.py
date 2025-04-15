"""Asynchronous I/O utilities."""

import asyncio

__all__ = [
    "yield_exec",
]

async def yield_exec():
    """Yields execution to other tasks in the event loop."""

    await asyncio.sleep(0)
