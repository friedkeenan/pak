import asyncio
import pak
import pytest

class DummyPacket(pak.Packet):
    class Context(pak.Packet.Context):
        def __init__(self, value=0):
            self.value = value

            super().__init__()

        def __hash__(self):
            return hash(self.value)

    class Header(pak.Packet.Header):
        id:   pak.UInt8
        size: pak.UInt8

class DummyValuePacket(DummyPacket):
    id = 0

    value: pak.UInt8

class DummyConnection(pak.io.Connection):
    def __init__(self, *, data=None, ctx=DummyPacket.Context()):
        reader = None
        writer = None

        if data is not None:
            reader = pak.io.ByteStreamReader(data)
            writer = pak.io.ByteStreamWriter()

        super().__init__(reader=reader, writer=writer, ctx=ctx)

    async def _read_next_packet(self):
        header_data = await self.read_data(DummyPacket.Header.size(ctx=self.ctx))
        if header_data is None:
            return None

        header = DummyPacket.Header.unpack(header_data, ctx=self.ctx)

        packet_data = await self.read_data(header.size)
        if packet_data is None:
            return None

        packet_cls = DummyPacket.subclass_with_id(header.id, ctx=self.ctx)

        return packet_cls.unpack(packet_data, ctx=self.ctx)

    async def write_packet_instance(self, packet):
        await self.write_data(packet.pack(ctx=self.ctx))

@pytest.mark.asyncio
async def test_connection_abc():
    with pytest.raises(TypeError, match="instantiate abstract"):
        pak.io.Connection()

    with pytest.raises(NotImplementedError):
        await pak.io.Connection._read_next_packet(object())

    with pytest.raises(NotImplementedError):
        await pak.io.Connection.write_packet_instance(object(), pak.Packet())

@pytest.mark.asyncio
async def test_connection_close():
    connection = DummyConnection()

    assert connection.reader is None
    assert connection.writer is None

    assert connection.is_closing()

    # Should do nothing with no writer.
    connection.close()
    await connection.wait_closed()

    connection.reader = pak.io.ByteStreamReader()
    connection.writer = pak.io.ByteStreamWriter()

    assert not connection.is_closing()

    class CloseSentinel:
        def __init__(self):
            self.writer     = False
            self.connection = False

    close_sentinel = CloseSentinel()

    async def set_writer_close_flag():
        await connection.writer.wait_closed()

        close_sentinel.writer = True

    async def set_connection_close_flag():
        await connection.wait_closed()

        close_sentinel.connection = True

    writer_close_task     = asyncio.create_task(set_writer_close_flag())
    connection_close_task = asyncio.create_task(set_connection_close_flag())

    # Give the tasks a chance to execute.
    await pak.util.yield_exec()

    assert not close_sentinel.writer
    assert not close_sentinel.connection

    connection.close()

    assert connection,is_closing()
    assert connection.writer.is_closing()

    # Give the tasks another chance to execute.
    await pak.util.yield_exec()

    assert close_sentinel.writer
    assert close_sentinel.connection

    await writer_close_task
    await connection_close_task

@pytest.mark.asyncio
async def test_connection_context():
    connection = DummyConnection(data=b"")

    class CloseSentinel:
        def __init__(self):
            self.flag = False

    close_sentinel = CloseSentinel()

    async def set_closed_flag():
        await connection.wait_closed()

        close_sentinel.flag = True

    set_closed_task = asyncio.create_task(set_closed_flag())

    # Give the task a chance to execute.
    await pak.util.yield_exec()

    assert not close_sentinel.flag

    async with connection:
        pass

    # Give the task another chance to execute.
    await pak.util.yield_exec()

    assert close_sentinel.flag

    await set_closed_task

def test_connection_create_packet():
    connection = DummyConnection(ctx=DummyPacket.Context(1))

    class TestContextPropagate(DummyPacket):
        value: pak.UInt8

        dummy: pak.UInt8

        def __init__(self, *, ctx, **fields):
            super().__init__(value=ctx.value, **fields)

    packet = connection.create_packet(
        TestContextPropagate,

        dummy = 2,
    )

    assert packet.value == 1
    assert packet.dummy == 2

@pytest.mark.asyncio
async def test_connection_read_data():
    connection = DummyConnection(data=b"abcd")

    assert await connection.read_data(3) == b"abc"

    assert await connection.read_data(2) is None

@pytest.mark.asyncio
async def test_connection_continuously_read_packets():
    connection = DummyConnection(
        # A single DummyValuePacket(value=2).
        data = b"\x00\x01\x02"
    )

    packet = None
    async for p in connection.continuously_read_packets():
        # Make sure we only run once.
        assert packet is None
        packet = p

    assert packet is not None
    assert packet == DummyValuePacket(value=2)

    assert connection.is_closing()

@pytest.mark.asyncio
async def test_connection_continuously_read_packets_ends_on_close():
    connection = DummyConnection(
        # A single DummyValuePacket(value=2).
        data = b"\x00\x01\x02"
    )

    iterations = 0
    async for packet in connection.continuously_read_packets():
        iterations += 1

        connection.close()

    assert iterations == 1

@pytest.mark.asyncio
async def test_connection_read_packet():
    connection = DummyConnection(
        # A single DummyValuePacket(value=2).
        data = b"\x00\x01\x02"
    )

    async def read_specific_packet():
        assert (
            await connection.read_packet(DummyValuePacket) == DummyValuePacket(value=2)
        )

        # There's only one packet in the stream.
        assert await connection.read_packet(DummyValuePacket) is None

    async def read_parent_packet():
        assert await connection.read_packet(DummyPacket) == DummyValuePacket(value=2)

    read_specific_packet_task = asyncio.create_task(read_specific_packet())
    read_parent_packet_task   = asyncio.create_task(read_parent_packet())

    # Needed to dispatch packets to 'read_packet'.
    async for packet in connection.continuously_read_packets():
        pass

    await read_specific_packet_task
    await read_parent_packet_task

@pytest.mark.asyncio
async def test_connection_read_packet_on_close():
    connection = DummyConnection(
        # A single DummyValuePacket(value=2).
        data = b"\x00\x01\x02"
    )

    async def read_specific_packet():
        assert await connection.read_packet(DummyValuePacket) is None

    read_specific_packet_task = asyncio.create_task(read_specific_packet())

    # Give the task a chance to execute.
    await pak.util.yield_exec()

    connection.close()

    await read_specific_packet_task

@pytest.mark.asyncio
async def test_connection_write_data():
    connection = DummyConnection(data=b"")

    await connection.write_data(b"abcd")

    assert connection.writer.written_data == b"abcd"

@pytest.mark.asyncio
async def test_connection_write_packet_instance():
    # This is technically testing our test code,
    # however it is added so that we can ensure
    # the written data lines up with the written
    # data when calling 'write_packet'.

    connection = DummyConnection(data=b"")

    await connection.write_packet_instance(DummyValuePacket(value=2))

    assert connection.writer.written_data == b"\x00\x01\x02"

@pytest.mark.asyncio
async def test_connection_write_packet():
    class CheckCreatePacket(DummyConnection):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

            self.created_packet = False

        def create_packet(self, packet_cls, **fields):
            self.created_packet = True

            return super().create_packet(packet_cls, **fields)

    connection = CheckCreatePacket(data=b"")

    assert not connection.created_packet

    await connection.write_packet(
        DummyValuePacket,

        value = 2,
    )

    assert connection.writer.written_data == b"\x00\x01\x02"

    assert connection.created_packet
