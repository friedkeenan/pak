import asyncio
import pak

async def test_yield_exec():
    class ExecSentinel:
        def __init__(self):
            self.flag = False

    exec_sentinel = ExecSentinel()

    async def set_exec_flag():
        exec_sentinel.flag = True

    exec_task = asyncio.create_task(set_exec_flag())

    # The task has not executed yet.
    assert not exec_sentinel.flag

    # Yield and let the task execute.
    await pak.util.yield_exec()

    # Make sure the task has executed.
    assert exec_sentinel.flag

    await exec_task

async def test_value_holder():
    async def set_holder_value(holder):
        holder.set(1)

    holder = pak.util.AsyncValueHolder()

    task = asyncio.create_task(set_holder_value(holder))

    assert await holder.get() == 1

    await task
