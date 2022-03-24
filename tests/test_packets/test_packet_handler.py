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
