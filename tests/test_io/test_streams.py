import asyncio
import pak
import pytest

async def test_byte_stream_reader_read():
    reader = pak.io.ByteStreamReader(b"abcd")

    assert not reader.at_eof()

    assert await reader.read(1) == b"a"
    assert await reader.read()  == b"bcd"

    assert reader.at_eof()
    assert await reader.read() == b""

async def test_byte_stream_reader_readline():
    reader = pak.io.ByteStreamReader(b"abcd\nefgh")

    assert await reader.readline() == b"abcd\n"
    assert await reader.readline() == b"efgh"

    assert reader.at_eof()

    assert await reader.readline() == b""

async def test_byte_stream_reader_readexactly():
    reader = pak.io.ByteStreamReader(b"abcd")

    assert await reader.readexactly(1) == b"a"

    with pytest.raises(asyncio.IncompleteReadError) as exc_info:
        await reader.readexactly(4)

    assert exc_info.value.partial  == b"bcd"
    assert exc_info.value.expected == 4

    assert reader.at_eof()
    assert await reader.readexactly(0) == b""

async def test_byte_stream_reader_readuntil():
    reader = pak.io.ByteStreamReader(b"abcd")

    assert await reader.readuntil(b"bc") == b"abc"

    with pytest.raises(ValueError, match="Separator.*one byte"):
        await reader.readuntil(b"")

    with pytest.raises(asyncio.IncompleteReadError) as exc_info:
        await reader.readuntil(b"e")

    assert exc_info.value.partial  == b"d"
    assert exc_info.value.expected is None

    assert reader.at_eof()

async def test_byte_stream_reader_readuntil_multiple():
    reader = pak.io.ByteStreamReader(b"abcd")

    assert await reader.readuntil((b"bc", b"bcd")) == b"abc"

    with pytest.raises(ValueError, match="Separator.*one byte"):
        await reader.readuntil((b"d", b""))

    with pytest.raises(asyncio.IncompleteReadError) as exc_info:
        await reader.readuntil((b"e", b"f"))

    assert exc_info.value.partial  == b"d"
    assert exc_info.value.expected is None

    assert reader.at_eof()

async def test_byte_stream_writer_close():
    writer = pak.io.ByteStreamWriter()

    assert not writer.is_closing()

    class ClosedSentinel:
        def __init__(self):
            self.flag = False

    closed_sentinel = ClosedSentinel()

    async def set_closed_flag():
        await writer.wait_closed()

        closed_sentinel.flag = True

    set_closed_task = asyncio.create_task(set_closed_flag())

    # Give 'set_closed_task' a chance to execute.
    await pak.util.yield_exec()

    # 'writer' is still not closed.
    assert not closed_sentinel.flag

    writer.close()
    assert writer.is_closing()

    # Give 'set_closed_task' another chance to execute.
    await pak.util.yield_exec()
    assert closed_sentinel.flag

    await set_closed_task

async def test_byte_stream_writer_write():
    writer = pak.io.ByteStreamWriter()

    assert writer.written_data == b""

    writer.write(b"abcd")
    await writer.drain()

    assert writer.written_data == b"abcd"

    writer.close()
    await writer.wait_closed()

    # Make sure we can still access the written data after closing.
    assert writer.written_data == b"abcd"

async def test_byte_stream_writer_writelines():
    writer = pak.io.ByteStreamWriter()

    writer.writelines([
        b"abcd",
        b"efgh",
    ])
    await writer.drain()

    assert writer.written_data == b"abcdefgh"

    writer.close()
    await writer.wait_closed()
