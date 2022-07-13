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

class GeneralPacket(Packet):
        pass

class DerivedPacket(GeneralPacket):
    pass

class MoreDerivedPacket(DerivedPacket):
    pass

class AdjacentDerivedPacket(GeneralPacket):
    pass

class UnrelatedPacket(Packet):
    pass

class MostDerivedHandler(PacketHandler):
    def __repr__(self):
        return "REPR"

    @most_derived_packet_listener(GeneralPacket)
    def most_derived(self):
        return GeneralPacket

    @most_derived.derived_listener(DerivedPacket)
    def most_derived(self):
        return DerivedPacket

    @most_derived.derived_listener(MoreDerivedPacket)
    def most_derived(self):
        return MoreDerivedPacket

    @most_derived.derived_listener(AdjacentDerivedPacket)
    def most_derived(self):
        return AdjacentDerivedPacket

def test_most_derived_packet_listener():
    assert repr(MostDerivedHandler.most_derived) == "<most_derived_packet_listener tests.test_packets.test_packet_handler.MostDerivedHandler.most_derived>"

    handler = MostDerivedHandler()

    assert repr(handler.most_derived) == "<bound most_derived_packet_listener MostDerivedHandler.most_derived of REPR>"

    assert handler.most_derived == handler.most_derived
    assert hash(handler.most_derived) == hash(handler.most_derived)
    with pytest.raises(TypeError, match="immutable"):
        handler.most_derived.attr = 1

    assert handler.is_listener_registered(handler.most_derived)

    assert handler.listeners_for_packet(GeneralPacket())[0]()         is GeneralPacket
    assert handler.listeners_for_packet(DerivedPacket())[0]()         is DerivedPacket
    assert handler.listeners_for_packet(MoreDerivedPacket())[0]()     is MoreDerivedPacket
    assert handler.listeners_for_packet(AdjacentDerivedPacket())[0]() is AdjacentDerivedPacket

    assert handler.listeners_for_packet(UnrelatedPacket) == []

def test_most_derived_packet_listener_override():
    with pytest.raises(ValueError, match="GeneralPacket"):
        class BadHandler(PacketHandler):
            @most_derived_packet_listener(GeneralPacket)
            def most_derived(self):
                pass

            @most_derived.derived_listener(GeneralPacket)
            def most_derived(self):
                pass

    class GoodHandler(PacketHandler):
        @most_derived_packet_listener(GeneralPacket)
        def most_derived(self):
            return "original"

        @most_derived.derived_listener(GeneralPacket, override=True)
        def most_derived(self):
            return "overridden"

    handler = GoodHandler()

    assert handler.listeners_for_packet(GeneralPacket())[0]() == "overridden"

def test_most_derived_packet_listener_not_subclass():
    with pytest.raises(ValueError, match="UnrelatedPacket.*GeneralPacket"):
        class BadHandler(PacketHandler):
            @most_derived_packet_listener(GeneralPacket)
            def most_derived(self):
                pass

            @most_derived.derived_listener(UnrelatedPacket)
            def most_derived(self):
                pass

    with pytest.raises(ValueError, match="GeneralPacket.*DerivedPacket"):
        class BadHandler(PacketHandler):
            @most_derived_packet_listener(DerivedPacket)
            def most_derived(self):
                pass

            @most_derived.derived_listener(GeneralPacket)
            def most_derived(self):
                pass

def test_most_derived_packet_listener_copies():
    class TestHandler(PacketHandler):
        @most_derived_packet_listener(GeneralPacket)
        def most_derived_orig(self):
            return GeneralPacket

        @most_derived_orig.derived_listener(DerivedPacket)
        def most_derived_new(self):
            return DerivedPacket

    assert TestHandler.most_derived_orig is not TestHandler.most_derived_new

    handler = TestHandler()

    general_listeners = handler.listeners_for_packet(GeneralPacket())
    derived_listeners = handler.listeners_for_packet(DerivedPacket())

    assert len(general_listeners) == 2
    assert len(derived_listeners) == 2

    # Both return 'GeneralPacket'.
    assert {listener() for listener in general_listeners} == {GeneralPacket}

    # One returns 'GeneralPacket', one returns 'DerivedPacket'.
    #
    # We shouldn't check the order of the listeners because that is a fragile
    # interface that ultimately depends on the alphabetical order of the listeners.
    assert {listener() for listener in derived_listeners} == {GeneralPacket, DerivedPacket}

def test_async_register():
    handler = AsyncPacketHandler()

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
