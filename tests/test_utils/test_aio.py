import asyncio
import pak
import pytest

@pytest.mark.asyncio
async def test_value_holder():
    async def set_holder_value(holder):
        holder.set(1)

    holder = pak.util.AsyncValueHolder()

    task = asyncio.create_task(set_holder_value(holder))

    assert await holder.get() == 1

    await task
