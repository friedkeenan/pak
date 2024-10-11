A Basic Protocol
================

Let's outline the packet protocol we're gonna be starting with. We'll start out with a fairly rudimentary protocol, the sort that would be used in a very simple app or tool.

In our protocol, there are two ends of communication: the client and the server. The client will send packets to the server, and the server will respond to the client with packets of its own. Both the client and server will know which specific packets are being sent and received beforehand. Throughout this, we will be acting as the server in our protocol.

So, what exactly is the protocol? Well, let's imagine that we, the server, own some sort of database, let's say that database contains a bunch of pictures of cats. The client will ask the server for information regarding this cat database, and the server will respond with the corresponding info.

First off, the client can send a packet to ask for the amount of cat pictures with a specific type of fur. This packet has an unsigned byte field for the type of fur: ``0`` for long-haired, ``1`` for short-haired, and ``2`` for medium-haired. Let's look at how we might define such a packet::

    import pak

    class CatPicturesRequest(pak.Packet):
        fur_type: pak.UInt8

Here we create the packet ``CatPicturesRequest`` with the field ``fur_type``, of type :class:`.UInt8`. This :class:`.Type` is provided by Pak, and represents an unsigned 8-bit integer.

The server should respond to a ``CatPicturesRequest`` packet with its own packet containing an unsigned 16-bit, little-endian field for the corresponding number of cat images. Let's see how we would define it::

    class CatPicturesResponse(pak.Packet):
        num_cat_pictures: pak.UInt16

Here we create the packet ``CatPicturesResponse`` with the field ``num_cat_pictures``, of type :class:`.UInt16`. This type is provided by Pak, and represents an unsigned 16-bit integer. Pak by default will interpret data according to little-`endian <https://en.wikipedia.org/wiki/Endianness>`_ byte order. Therefore, we can just use :class:`.UInt16` as is. However, if we *did* need to use big-endian, we could do so like this::

    class CatPicturesResponse(pak.Packet):
        num_cat_pictures: pak.UInt16.big_endian()

Here we use the :meth:`.StructType.big_endian` method to get a big-endian version of :class:`.UInt16`, and use that for the ``num_cat_pictures`` field. We could alternatively do this::

    class UInt16_BE(pak.UInt16):
        endian = ">"

and use ``UInt16_BE`` instead in our packet definition. With ``endian = ">"`` we set the endianness to big-endian, using the same symbol as you would find with the standard :mod:`struct` module to specify endianness. Defining this ``UInt16_BE`` class would be basically equivalent to doing ``UInt16_BE = pak.UInt16.big_endian()``.

.. _basic-send-receive-packets:

Sending and Receiving Packets
*****************************

But how would we, the server, go about receiving and handling the ``CatPicturesRequest`` packet? Well, since we already know what packets the client is sending beforehand, we could define a function to read a packet::

    # A function which reads 'size' bytes from
    # the client. It is not important to us how
    # it is implemented.
    def read_data(size):
        ...

    # This is the function that will read a
    # packet from the client.
    def read_packet(packet_cls):
        # Get the size of the packet so we
        # know how many bytes to read.
        packet_size = packet_cls.size()

        # Get the packet data from the client.
        packet_data = read_data(packet_size)

        # Unpack the packet from the data and return it.
        return packet_cls.unpack(packet_data)

We could also define a function to write a packet::

    # A function which writes 'data' to the client.
    # It is not important to us how it is implemented.
    def write_data(data):
        ...

    # This is the function that will write a packet
    # to the client.
    def write_packet(packet):
        # Pack the packet into raw data.
        packet_data = packet.pack()

        # Write the packet data to the client.
        write_data(packet_data)

And then the code to handle the packet could look like this::

    packet = read_packet(CatPicturesRequest)

    if packet.fur_type == 0:
        # Get number of long-haired pictures.
        num_pictures = ...

    elif packet.fur_type == 1:
        # Get number of short-haired pictures.
        num_pictures = ...

    elif packet.fur_type == 2:
        # Get number of medium-haired pictures.
        num_pictures = ...

    write_packet(
        CatPicturesResponse(num_cat_pictures=num_pictures)
    )


Doing Better: Enumerations
**************************

We could stop where we are here; we're certainly conforming to the protocol as we've laid it out. But, it kind of sucks to just use magic, unnamed values for the fur type. You may already realize this, but the ``fur_type`` field acts much like an "enumeration" does. It has a set of constant, enumerated values with special meaning. Pak has a way of describing this using the :class:`.Enum` field type, which piggybacks off of the standard :mod:`enum` module. Let's see how we would define ``CatPicturesRequest`` using it:

.. testcode::

    import pak
    import enum

    class FurType(enum.Enum):
        LongHaired   = 0
        ShortHaired  = 1
        MediumHaired = 2

    class CatPicturesRequest(pak.Packet):
        fur_type: pak.Enum(pak.UInt8, FurType)

First, we create the ``FurType`` class, which inherits from :class:`enum.Enum`, enumerating the ``LongHaired``, ``ShortHaired``, and ``MediumHaired`` values. We then define the ``CatPicturesRequest`` packet, with the field ``fur_type`` of type ``pak.Enum(pak.UInt8, FurType)``.

This reveals an aspect of :class:`.Type`\s that we have not covered: They may be callable, returning new :class:`.Type`\s. When callable, they may just make it so you can customize aspects of the original :class:`.Type`, or they may allow you to compose :class:`.Type`\s to layer functionality. :class:`.Enum` allows the latter. The first argument is the "underlying type" of the :class:`.Enum`, which tells it how to marshal the enum values, and then the second argument is the :class:`enum.Enum` class to map values to.

Thus, in our new ``CatPicturesRequest`` definition, the ``fur_type`` field will be marshaled according to the :class:`.UInt8` type, but have values of ``FurType``. To demonstrate:

.. testcode::

    # An unsigned byte value of '1'.
    raw_data = b"\x01"

    packet = CatPicturesRequest.unpack(raw_data)
    assert packet == CatPicturesRequest(fur_type=FurType.ShortHaired)

Here, the raw data of ``b"\x01"`` is unpacked according to :class:`.UInt8`, and then the resulting value of ``1`` is converted to a ``FurType`` value, in this case ``FurType.ShortHaired``.

So now with our new definition of ``CatPicturesRequest``, we can rewrite our serverside handling code::

    packet = read_packet(CatPicturesRequest)

    if packet.fur_type is FurType.LongHaired:
        num_pictures = ...

    elif packet.fur_type is FurType.ShortHaired:
        num_pictures = ...

    elif packet.fur_type is FurType.MediumHaired:
        num_pictures = ...

    write_packet(
        CatPicturesResponse(num_cat_pictures=num_pictures)
    )

This code is *much* more readable. It could even be made more readable with ``match`` statements introduced in Python 3.10, though that is left as an exercise for the reader.

----

But let's say somehow, when we, the server, try to read the ``CatPicturesRequest`` packet, the data we get is ``b"\x03"``, corresponding to an unsigned byte value of ``3``. This could happen for instance if the client is using a newer version of the protocol that uses the value ``3`` to ask for the number of *hairless* cat pictures, or perhaps we're communicating with a malicious client who's trying to expose flaws in our code by sending unexpected values. Let's see what happens:

.. testcode::

    # An unsigned byte value of '3'.
    raw_data = b"\x03"

    packet = CatPicturesRequest.unpack(raw_data)
    print(packet)

The output:

.. testoutput::

    CatPicturesRequest(fur_type=INVALID)

So what's happening here? Well, the :class:`.Enum` type has a special value that will be unpacked when the underlying type unpacks a value that isn't valid for the :class:`enum.Enum` class: :attr:`.Enum.INVALID`. This is a singleton value, meaning you can compare against it using identity (with the ``is`` operator).

So let's modify our handling code to account for invalid values::

    packet = read_packet(CatPicturesRequest)

    if packet.fur_type is FurType.LongHaired:
        num_pictures = ...

    elif packet.fur_type is FurType.ShortHaired:
        num_pictures = ...

    elif packet.fur_type is FurType.MediumHaired:
        num_pictures = ...

    elif packet.fur_type is pak.Enum.INVALID:
        # If we receive an invalid fur type,
        # just report we have 0 pictures.
        num_pictures = 0

    write_packet(
        CatPicturesResponse(num_cat_pictures=num_pictures)
    )

This handles all cases, but it would probably be prudent to refactor all of our code so far as so::

    import pak
    import enum

    class FurType(enum.Enum):
        LongHaired   = 0
        ShortHaired  = 1
        MediumHaired = 2

    class CatPicturesRequest(pak.Packet):
        fur_type: pak.Enum(pak.UInt8, FurType)

    class CatPicturesResponse(pak.Packet):
        num_cat_pictures: pak.UInt16

    # A function which reads 'size' bytes from
    # the client. It is not important to us how
    # it is implemented.
    def read_data(size):
        ...

    # This is the function that will read a
    # packet from the client.
    def read_packet(packet_cls):
        # Get the size of the packet so we
        # know how many bytes to read.
        packet_size = packet_cls.size()

        # Get the packet data from the client.
        packet_data = read_data(packet_size)

        # Unpack the packet from the data and return it.
        return packet_cls.unpack(packet_data)

    # A function which writes 'data' to the client.
    # It is not important to us how it is implemented.
    def write_data(data):
        ...

    # This is the function that will write a packet
    # to the client.
    def write_packet(packet):
        # Pack the packet into raw data.
        packet_data = packet.pack()

        # Write the packet data to the client.
        write_data(packet_data)

    # Gets the number of cat pictures with a certain fur type.
    def get_num_cat_pictures(fur_type):
        ...

    # The function to handle a 'CatPicturesRequest' packet.
    def handle_request():
        packet = read_packet(CatPicturesRequest)

        if packet.fur_type is pak.Enum.INVALID:
            # If we receive an invalid fur type,
            # just report we have 0 pictures.
            num_pictures = 0

        else:
            num_pictures = get_num_cat_pictures(packet.fur_type)

        write_packet(
            CatPicturesResponse(num_cat_pictures=num_pictures)
        )

----

And there we have it; now we have some spiffy, readable code that adequately conforms to the protocol as we've laid it out. But what if we decided that instead of sending the *number* of cat pictures we have with a certain fur type, we wanted to send all the *URLs* to the cat pictures? Move on to :doc:`stringy` to explore that avenue.
