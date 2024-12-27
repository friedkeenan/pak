Getting a Handle on Things
==========================

For this section, we will be working with protocol version ``0`` established in :doc:`identifying`. This leaves us with the following Pak specification:

.. testcode::

    import enum
    import pak

    String = pak.PrefixedString(pak.UInt8)

    class FurType(enum.Enum):
        LongHaired   = 0
        ShortHaired  = 1
        MediumHaired = 2

    class FelinePacket(pak.Packet):
        class Header(pak.Packet.Header):
            id:   pak.UInt8
            size: pak.UInt8

    class ServerboundFelinePacket(FelinePacket):
        pass

    class ClientboundFelinePacket(FelinePacket):
        pass

    class CatIDsRequest(ServerboundFelinePacket):
        id = 0

        fur_type: pak.Enum(pak.UInt8, FurType)

    class CatIDsResponse(ClientboundFelinePacket):
        id = 0

        fur_type: pak.Enum(pak.UInt8, FurType)
        cat_ids:  pak.UInt16[None]

    class CatInfoRequest(ServerboundFelinePacket):
        id = 1

        cat_id: pak.UInt16

    class CatInfoResponse(ClientboundFelinePacket):
        id = 1

        cat_id:      pak.UInt16
        picture_url: String

        # The cat's birth date is represented by
        # a 'UInt16' for the year, a 'UInt8' for
        # the month, and a 'UInt8' for the day.

        birth_year:  pak.UInt16
        birth_month: pak.UInt8
        birth_day:   pak.UInt8


As a reminder, ``CatIDsRequest`` is a packet sent to the server to request a list of IDs for cats which have a certain fur type. ``CatIDsResponse`` is sent to the client with a list of appropriate cat IDs, and the corresponding fur type. ``CatInfoRequest`` is a packet sent to the server which requests information for a particular cat, specified by its ID, and ``CatInfoResponse`` is sent to the client with the corresponding information.

So how would we go about handling these packets?

----

To handle an incoming packet, we, the server, might do something like this::

    packet = read_packet()

    if isinstance(packet, CatIDsRequest):
        write_packet(CatIDsResponse(...))

    elif isinstance(packet, CatInfoRequest):
        write_packet(CatInfoResponse(...))

And this is basically fine enough for the limited amount of packets we have. But if we were to have many packets, one can easily see that we would end up with a lengthy ``if``/``elif`` chain, which would also be very imperative and not the easiest to read. That could maybe be managed with a ``match`` statement (a Python 3.10+ feature), but it would still result in a lengthy bit of code that isn't very extensible. Imagine you were creating a library, and you wanted users to be able to handle packets their own way. They can't in good conscience edit your code to add onto your ``if``/``elif`` chain or your ``match`` statement. It's very hard for this approach to maintain coherence at scale.

Doing Better: Packet Handlers
*****************************

Pak luckily provides a mechanism to handle packets at scale: :class:`.PacketHandler`. With a :class:`.PacketHandler`, we can register "packet listeners" that will listen to packets in a scalable way. Let's look at how we might use it:

.. testcode::

    import pak

    class FelinePacketHandler(pak.PacketHandler):
        @pak.packet_listener(CatIDsRequest)
        def on_ids_request(self, packet):
            write_packet(CatIDsResponse(...))

        @pak.packet_listener(CatInfoRequest)
        def on_info_request(self, packet):
            write_packet(CatInfoResponse(...))

We create a subclass of :class:`.PacketHandler`, and add methods decorated with :func:`.packet_listener`. These methods will be registered as packet listeners once our ``FelinePacketHandler`` is constructed. The arguments to :func:`.packet_listener` are the types a packet must be an instance of so that they will be listened to by that method. So when we receive a ``CatIDsRequest`` packet, ``FelinePacketHandler.on_ids_request`` will be the correct listener, and for a ``CatInfoRequest`` packet, ``FelinePacketHandler.on_info_request`` would be the correct listener.

.. note::

    The correct listener would in fact be the **bound** methods decorated by :func:`.packet_listener`, bound to our ``FelinePacketHandler`` instance.

In order to get the corresponding listeners for a packet, one can use the :meth:`.PacketHandler.listeners_for_packet` method. It takes in a :class:`.Packet`, some "flags" that we will get to in a moment, and returns a list of appropriate listeners for the packet and flags:

.. testcode::

    handler = FelinePacketHandler()

    ids_request_listeners = handler.listeners_for_packet(CatIDsRequest())
    assert ids_request_listeners == [handler.on_ids_request]

    info_request_listeners = handler.listeners_for_packet(CatInfoRequest())
    assert info_request_listeners == [handler.on_info_request]

After getting the appropriate listeners for a packet, you can use it however you want; in our case we would want to call it, passing the packet to it. Code to read and listen to our packets might end up looking something like this::

    class FelinePacketHandler(pak.PacketHandler):
        def listen_to_incoming_packets(self):
            while True:
                packet = read_packet()

                for listener in self.listeners_for_packet(packet):
                    listener(packet)

        @pak.packet_listener(CatIDsRequest)
        def on_ids_request(self, packet):
            write_packet(CatIDsResponse(...))

        @pak.packet_listener(CatInfoRequest)
        def on_info_request(self, packet):
            write_packet(CatInfoResponse(...))

    ...

    handler = FelinePacketHandler()
    handler.listen_to_incoming_packets()

Such code also provides a nice way to maintain state between listening to different packets, as different things could be kept track of within our ``handler`` object.

----

Packet listeners can also be associated with certain "flags" that must match with the flags passed to :meth:`.PacketHandler.listeners_for_packet`. For instance, if we wanted to have listeners for outgoing packets as well as incoming packets, we might have a flag called ``outgoing`` which would be either ``True`` or ``False``, and would be used like so::

    class FelinePacketHandler(pak.PacketHandler):
        def write_packet(self, packet):
            # We use this method to call packet listeners for outgoing packets.

            for listener in self.listeners_for_packet(packet, outgoing=True):
                listener(packet)

            # Call the function that actually sends the packet.
            write_packet(packet)

        def listen_to_incoming_packets(self):
            while True:
                packet = read_packet()

                for listener in self.listeners_for_packet(packet, outgoing=False):
                    listener(packet)

        @pak.packet_listener(CatIDsRequest, outgoing=False)
        def on_ids_request(self, packet):
            self.write_packet(CatIDsResponse(...))

        @pak.packet_listener(CatInfoRequest, outgoing=False)
        def on_info_request(self, packet):
            self.write_packet(CatInfoResponse(...))

This would then let us leverage our packet listening infrastructure for packets we send too, which could for instance be used for debugging purposes to print all the packets we send or to otherwise have special logic for whenever we send a certain packet. Here our listeners would only be called when receiving packets, because they have the ``outgoing`` flag set to ``False``. Since it's annoying and error-prone to always specify the ``outgoing`` flag, we can make it default to ``False`` (or make specifying it required if we wanted to) by overriding the :meth:`.PacketHandler.register_packet_listener` method, like so::

    class FelinePacketHandler(pak.PacketHandler):
        def register_packet_listener(self, listener, *packet_types, outgoing=False, **flags):
            super().register_packet_listener(
                listener,
                *packet_types,
                outgoing=outgoing,
                **flags,
            )

        ...

This works because upon constructing a :class:`.PacketHandler`, methods that are decorated with :func:`.packet_listener` will be registered using :meth:`.PacketHandler.register_packet_listener`. You also can use that method to register packet listeners without the :func:`.packet_listener` decorator, like so::

    handler = FelinePacketHandler()

    def on_info_response(packet):
        ...

    handler.register_packet_listener(on_info_response, CatInfoResponse, outgoing=True)

That's All Folks
****************

And that's it, that's the end of the :doc:`index` tutorials. There is still more to Pak that has not been covered, but you should now be very well-equipped to look through the :doc:`../../reference` to investigate its other features (in particular :class:`.SubPacket` and :class:`io.Connection <.Connection>` might be good to look at), and hopefully you now have a strong core of knowledge to put towards your own projects.

Thank you, and I wish you well.
