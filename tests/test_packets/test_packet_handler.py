import asyncio
import pytest
from pak import *

def test_register():
    def listener(packet):
        pass

    handler = PacketHandler()

    with pytest.raises(TypeError):
        # No packet types passed.
        handler.register_packet_listener(listener)

    handler.register_packet_listener(listener, Packet)

    assert handler.is_listener_registered(listener)

    with pytest.raises(ValueError, match="registered"):
        # 'listener' is already registered.
        handler.register_packet_listener(listener, Packet)

    handler.unregsiter_packet_listener(listener)

    assert not handler.is_listener_registered(listener)

def test_listeners_for_packet():
    def listener(packet):
        pass

    handler = PacketHandler()
    handler.register_packet_listener(listener, Packet, flag=True)

    assert handler.listeners_for_packet(Packet())             == []
    assert handler.listeners_for_packet(Packet(), flag=False) == []

    assert handler.listeners_for_packet(Packet(), flag=True) == [listener]

def test_async_register():
    def non_async_listener(packet):
        pass

    handler = AsyncPacketHandler()

    with pytest.raises(TypeError, match="non_async_listener"):
        handler.register_packet_listener(non_async_listener, Packet)

    async def async_listener(packet):
        pass

    handler.register_packet_listener(async_listener, Packet)
    assert handler.is_listener_registered(async_listener)

@pytest.mark.asyncio
async def test_async_listener_tasks():
    handler = AsyncPacketHandler()
    packet  = Packet()

    async def unending_listener(packet):
        packet.executed_task = True

        while True:
            await asyncio.sleep(0)

    handler.register_packet_listener(unending_listener, Packet)
    async with handler.listener_task_context(listen_sequentially=False):
        for listener in handler.listeners_for_packet(packet):
            handler.create_listener_task(listener(packet))

    try:
        await asyncio.wait_for(handler.end_listener_tasks(timeout=0), timeout=1)

    except asyncio.TimeoutError:
        # This should never happen since the listener tasks should be canceled.
        assert False

    assert packet.executed_task

    # TODO: Figure out how to test listening sequentially.
