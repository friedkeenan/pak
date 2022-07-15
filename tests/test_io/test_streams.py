import asyncio
import pak
import pytest

@pytest.mark.asyncio
async def test_byte_stream_reader_read():
    reader = pak.io.ByteStreamReader(b"abcd")

    assert not reader.at_eof()

    assert await reader.read(1) == b"a"
    assert await reader.read()  == b"bcd"
    assert await reader.read()  == b""

    assert reader.at_eof()

@pytest.mark.asyncio
async def test_byte_stream_reader_readline():
    reader = pak.io.ByteStreamReader(b"abcd\nefgh")

    assert await reader.readline() == b"abcd\n"
    assert await reader.readline() == b"efgh"

    assert reader.at_eof()

@pytest.mark.asyncio
async def test_byte_stream_reader_readexactly():
    reader = pak.io.ByteStreamReader(b"abcd")

    assert await reader.readexactly(1) == b"a"

    with pytest.raises(asyncio.IncompleteReadError) as exc_info:
        await reader.readexactly(4)

    assert exc_info.value.partial  == b"bcd"
    assert exc_info.value.expected == 4

    assert await reader.readexactly(0) == b""
    assert reader.at_eof()

@pytest.mark.asyncio
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
