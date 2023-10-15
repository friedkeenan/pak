import asyncio
import pak
import pytest

def test_register():
    def listener(packet):
        pass

    handler = pak.PacketHandler()

    with pytest.raises(TypeError):
        # No packet types passed.
        handler.register_packet_listener(listener)

    handler.register_packet_listener(listener, pak.Packet)

    assert handler.is_listener_registered(listener)

    with pytest.raises(ValueError, match="registered"):
        # 'listener' is already registered.
        handler.register_packet_listener(listener, pak.Packet)

    handler.unregister_packet_listener(listener)

    assert not handler.is_listener_registered(listener)

def test_listeners_for_packet():
    def listener(packet):
        pass

    handler = pak.PacketHandler()
    handler.register_packet_listener(listener, pak.Packet, flag=True)

    assert handler.listeners_for_packet(pak.Packet())             == []
    assert handler.listeners_for_packet(pak.Packet(), flag=False) == []

    assert handler.listeners_for_packet(pak.Packet(), flag=True) == [listener]

    assert handler.listeners_for_packet(pak.Packet)             == []
    assert handler.listeners_for_packet(pak.Packet, flag=False) == []

    assert handler.listeners_for_packet(pak.Packet, flag=True) == [listener]

def test_has_packet_listener():
    def listener(packet):
        pass

    handler = pak.PacketHandler()
    handler.register_packet_listener(listener, pak.Packet, flag=True)

    assert not handler.has_packet_listener(pak.Packet())
    assert not handler.has_packet_listener(pak.Packet(), flag=False)

    assert handler.has_packet_listener(pak.Packet(), flag=True)

    assert not handler.has_packet_listener(pak.Packet)
    assert not handler.has_packet_listener(pak.Packet, flag=False)

    assert handler.has_packet_listener(pak.Packet, flag=True)

class GeneralPacket(pak.Packet):
        pass

class DerivedPacket(GeneralPacket):
    pass

class MoreDerivedPacket(DerivedPacket):
    pass

class AdjacentDerivedPacket(GeneralPacket):
    pass

class UnrelatedPacket(pak.Packet):
    pass

class MostDerivedHandler(pak.PacketHandler):
    def __repr__(self):
        return "REPR"

    @pak.most_derived_packet_listener(GeneralPacket)
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
        class BadHandler(pak.PacketHandler):
            @pak.most_derived_packet_listener(GeneralPacket)
            def most_derived(self):
                pass

            @most_derived.derived_listener(GeneralPacket)
            def most_derived(self):
                pass

    class GoodHandler(pak.PacketHandler):
        @pak.most_derived_packet_listener(GeneralPacket)
        def most_derived(self):
            return "original"

        @most_derived.derived_listener(GeneralPacket, override=True)
        def most_derived(self):
            return "overridden"

    handler = GoodHandler()

    assert handler.listeners_for_packet(GeneralPacket())[0]() == "overridden"

def test_most_derived_packet_listener_not_subclass():
    with pytest.raises(ValueError, match="UnrelatedPacket.*GeneralPacket"):
        class BadHandler(pak.PacketHandler):
            @pak.most_derived_packet_listener(GeneralPacket)
            def most_derived(self):
                pass

            @most_derived.derived_listener(UnrelatedPacket)
            def most_derived(self):
                pass

    with pytest.raises(ValueError, match="GeneralPacket.*DerivedPacket"):
        class BadHandler(pak.PacketHandler):
            @pak.most_derived_packet_listener(DerivedPacket)
            def most_derived(self):
                pass

            @most_derived.derived_listener(GeneralPacket)
            def most_derived(self):
                pass

def test_most_derived_packet_listener_copies():
    class TestHandler(pak.PacketHandler):
        @pak.most_derived_packet_listener(GeneralPacket)
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

@pytest.mark.asyncio
async def test_async_listener_tasks():
    handler = pak.AsyncPacketHandler()

    async def unending_listener():
        while True:
            await pak.util.yield_exec()

    handler.register_packet_listener(unending_listener, pak.Packet)
    async with handler.listener_task_group(listen_sequentially=False) as group:
        for listener in handler.listeners_for_packet(pak.Packet()):
            unending_listener_task = group.create_task(listener())

    assert not unending_listener_task.done()

    try:
        await asyncio.wait_for(handler.end_listener_tasks(timeout=0), timeout=1)

    except asyncio.TimeoutError:
        # This should never happen since the listener tasks should be canceled.
        assert False

    assert unending_listener_task.done()

@pytest.mark.asyncio
async def test_async_listener_nonsequential_tasks_forward_return():
    handler = pak.AsyncPacketHandler()

    async def returning_listener():
        return 1

    handler.register_packet_listener(returning_listener, pak.Packet)
    async with handler.listener_task_group(listen_sequentially=False) as group:
        for listener in handler.listeners_for_packet(pak.Packet()):
            returning_listener_task = group.create_task(listener())

    await handler.end_listener_tasks()

    assert returning_listener_task.result() == 1

@pytest.mark.asyncio
async def test_async_listener_tasks_sequential():
    handler = pak.AsyncPacketHandler()

    async def yielding_listener():
        await pak.util.yield_exec()

        return 1

    handler.register_packet_listener(yielding_listener, pak.Packet)
    async with handler.listener_task_group(listen_sequentially=True) as group:
        for listener in handler.listeners_for_packet(pak.Packet()):
            yielding_listener_task = group.create_task(listener())

    assert yielding_listener_task.done()
    assert not yielding_listener_task.cancelled()

    # Make sure the return value is forwarded.
    assert yielding_listener_task.result() == 1

@pytest.mark.asyncio
async def test_async_listener_tasks_sequential_independent():
    handler = pak.AsyncPacketHandler()

    async def sequential_listener():
        # NOTE: Unfortunately this touches an implementation
        # detail to see if sequential listener tasks are
        # independent. The only alternative I can think of
        # would be to have a test that loops forever if it
        # fails, which sucks. I don't know which is better.
        # Probably this.
        assert len(handler._listener_tasks) == 0

        await pak.util.yield_exec()

    handler.register_packet_listener(sequential_listener, pak.Packet)

    async with handler.listener_task_group(listen_sequentially=True) as group:
        for listener in handler.listeners_for_packet(pak.Packet()):
            sequential_task = group.create_task(listener())

    assert sequential_task.done()
    assert not sequential_task.cancelled()
