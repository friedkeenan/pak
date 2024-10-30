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

        def __eq__(self, other):
            if not isinstance(other, type(self)):
                return NotImplemented

            return self.value == other.value

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

async def test_connection_abc():
    with pytest.raises(TypeError, match="instantiate abstract"):
        pak.io.Connection()

    with pytest.raises(NotImplementedError):
        await pak.io.Connection._read_next_packet(object())

    with pytest.raises(NotImplementedError):
        await pak.io.Connection.write_packet_instance(object(), pak.Packet())

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

def test_connection_create_packet_positional_only():
    class TestPositionalPacket(DummyPacket):
        packet_cls: pak.UInt8

    # We can use the 'packet_cls' field despite
    # that it's the name of the initial parameter.
    packet = DummyConnection().create_packet(
        TestPositionalPacket,

        packet_cls = 1,
    )

    assert packet.packet_cls == 1

async def test_connection_read_data():
    connection = DummyConnection(data=b"abcd")

    assert await connection.read_data(3) == b"abc"

    assert await connection.read_data(2) is None

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

async def test_connection_watch_for_packet():
    connection = DummyConnection(
        # A single DummyValuePacket(value=2).
        data = b"\x00\x01\x02"
    )

    async def watch_for_packet():
        assert (
            await connection.watch_for_packet(DummyValuePacket) == DummyValuePacket(value=2)
        )

        # There's only one packet in the stream.
        assert await connection.watch_for_packet(DummyValuePacket) is None

    async def watch_for_parent_packet():
        assert await connection.watch_for_packet(DummyPacket) == DummyValuePacket(value=2)

    watch_for_packet_task        = asyncio.create_task(watch_for_packet())
    watch_for_parent_packet_task = asyncio.create_task(watch_for_parent_packet())

    # Needed to dispatch packets to 'watch_for_packet'.
    async for packet in connection.continuously_read_packets():
        pass

    await watch_for_packet_task
    await watch_for_parent_packet_task

async def test_connection_watch_for_packet_on_close():
    connection = DummyConnection(
        # A single DummyValuePacket(value=2).
        data = b"\x00\x01\x02"
    )

    async def watch_for_packet():
        assert await connection.watch_for_packet(DummyValuePacket) is None

    watch_for_packet_task = asyncio.create_task(watch_for_packet())

    # Give the task a chance to execute.
    await pak.util.yield_exec()

    connection.close()

    await watch_for_packet_task

async def test_connection_is_watching_for_packet():
    connection = DummyConnection(data=b"")

    async def watch_for_packet():
        await connection.watch_for_packet(DummyPacket)

    watch_for_packet_task = asyncio.create_task(watch_for_packet())

    # Give the task a chance to execute.
    await pak.util.yield_exec()

    assert connection.is_watching_for_packet(DummyPacket)
    assert connection.is_watching_for_packet(DummyValuePacket)

    assert not connection.is_watching_for_packet(pak.Packet)

    # Try to continuously read packets, which will immediately
    # reach EOF and cancel all the packet watches.
    async for packet in connection.continuously_read_packets():
        pass

    await watch_for_packet_task

async def test_connection_write_data():
    connection = DummyConnection(data=b"")

    await connection.write_data(b"abcd")

    assert connection.writer.written_data == b"abcd"

async def test_connection_write_packet_instance():
    # This is technically testing our test code,
    # however it is added so that we can ensure
    # the written data lines up with the written
    # data when calling 'write_packet'.

    connection = DummyConnection(data=b"")

    await connection.write_packet_instance(DummyValuePacket(value=2))

    assert connection.writer.written_data == b"\x00\x01\x02"

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

# The asynchronous unpacking API was motivated by the packet
# protocol for the CTF game 'Pwn Adventure 3: Pwnie Island'
# which has packets that do not report their size in their
# header but that nonetheless still have a dynamic size,
# which massively complicated the process of sanely unpacking
# them from an 'asyncio.StreamReader', and therefore a 'pak.io.Connection'.
#
# Thus we test here a similar sort of protocol
# to make sure that we can handle such a case.

class UnsizedPacket(pak.Packet):
    class Header(pak.Packet.Header):
        id: pak.UInt8

class UnsizedStringPacket(UnsizedPacket):
    id = 1

    string: pak.TerminatedString

# Test to make sure we can define custom field types
# as expected using the asynchronous API and whatnot.
class UnsizedCustomTypePacket(UnsizedPacket):
    id = 2

    # Takes a 'TerminatedString' and splits it into a list.
    class CustomType(pak.Type):
        @classmethod
        async def _unpack_async(cls, reader, *, ctx):
            return (await pak.TerminatedString.unpack_async(reader, ctx=ctx)).split()

        @classmethod
        def _pack(cls, value, *, ctx):
            return pak.TerminatedString.pack(" ".join(value), ctx=ctx)

    custom: CustomType

class UnsizedConnection(pak.io.Connection):
    def __init__(self, *, data=None, ctx=UnsizedPacket.Context()):
        reader = None
        writer = None

        if data is not None:
            reader = pak.io.ByteStreamReader(data)
            writer = pak.io.ByteStreamWriter()

        super().__init__(reader=reader, writer=writer, ctx=ctx)

    async def _read_next_packet(self):
        header_data = await self.read_data(UnsizedPacket.Header.size(ctx=self.ctx))
        if header_data is None:
            return None

        header = UnsizedPacket.Header.unpack(header_data, ctx=self.ctx)

        packet_cls = UnsizedPacket.subclass_with_id(header.id, ctx=self.ctx)

        return await packet_cls.unpack_async(self.reader, ctx=self.ctx)

    async def write_packet_instance(self, packet):
        await self.write_data(packet.pack(ctx=self.ctx))

async def test_unsized_connection():
    connection = UnsizedConnection(
        data = (
            b"\x01" + b"test\x00" +

            b"\x01" + b"another test\x00" +

            b"\x02" + b"yet another test\x00"
        )
    )

    packets = []
    async for packet in connection.continuously_read_packets():
        packets.append(packet)

    assert packets == [
        UnsizedStringPacket(string="test"),

        UnsizedStringPacket(string="another test"),

        UnsizedCustomTypePacket(custom=["yet", "another", "test"])
    ]
