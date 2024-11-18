A Stringy Protocol
==================

To recap where we left off from :doc:`basic`, we have the following two packets so far::

    class FurType(enum.Enum):
        LongHaired   = 0
        ShortHaired  = 1
        MediumHaired = 2

    class CatPicturesRequest(pak.Packet):
        fur_type: pak.Enum(pak.UInt8, FurType)

    class CatPicturesResponse(pak.Packet):
        num_cat_pictures: pak.UInt16

``CatPicturesRequest`` is sent by the client to the server in order to ask how many cat pictures there are with a certain fur type. ``CatPicturesResponse`` is then sent by the server to the client in order to convey how many corresponding pictures there are.

Now we want to change our protocol so that when ``CatPicturesRequest`` is sent by the client, the server responds with all the URLs of the cat pictures instead of just the count.

Anatomy of a String
*******************

The URLs of our cat pictures are strings, so we need to figure out how a string field would be structured.

There are several relatively reasonable ways strings can be represented. You could just have the string data simply suffixed with a null-terminator, so a string like ``"Hello"`` would marshal to ``b"Hello\x00"``, and the string :class:`.Type` would just read until the null-terminator. You could have a string that always takes up a certain amount of raw data but is still suffixed with a null-terminator, so if you had a string that always took up 8 bytes (including the null-terminator), a string like ``"Hello"`` would marshal to something like ``b"Hello\x00\xFF\xFF"`` where the ``\xFF`` bytes represent garbage data after the null-terminator. There are several more ways a string could be marshaled, but here's the method our protocol will be using:

First, there is an unsigned byte which tells the length of the string data. Next comes the string data, encoded according to UTF-8. Therefore, a string like ``"Hello"`` would get marshaled to ``b"\x05Hello"``. Pretty simple.

----

So how would we go about modeling this sort of string? We would want some sort of :class:`.Type` in order to marshal between string values and raw data, so I suppose let's create our own.

The first thing to know about custom :class:`.Type`\s is that all :class:`.Type`\s are classes, inheriting from :class:`.Type`, so, to start, our custom ``String`` type could look like this::

    import pak

    class String(pak.Type):
        pass

But with just this, we are missing the ability to unpack raw data and to pack values. To add that functionality, we would need to override the :meth:`.Type._unpack` and :meth:`.Type._pack` class methods::

    import pak

    class String(pak.Type):
        @classmethod
        def _unpack(cls, buf, *, ctx):
            ...

        @classmethod
        def _pack(cls, value, *, ctx):
            ...

Let's look at the ``_unpack`` method first. It has three parameters: ``cls``, the class for which the method is being invoked (our ``String`` class), ``buf``, which is a binary file object containing the raw data to unpack, and then there is the keyword-only ``ctx`` parameter which we will gloss over for now. Our ``_unpack`` method should return the value which corresponds to the passed raw data.

For the ``_pack`` method, we have the ``cls`` parameter, which again is the class for which the method is being invoked, ``value`` which is the value we are packing, and then another keyword-only ``ctx`` parameter. Our ``_pack`` method should return the raw data (of type :class:`bytes`) which corresponds to the passed value.

So let's fill in our methods:

.. testcode::

    import pak

    class String(pak.Type):
        @classmethod
        def _unpack(cls, buf, *, ctx):
            # Unpack the length of the string data.
            data_length = pak.UInt8.unpack(buf, ctx=ctx)

            # Read the string data.
            data = buf.read(data_length)

            # Decode the data into a string and return it.
            return data.decode("utf-8")

        @classmethod
        def _pack(cls, value, *, ctx):
            # Encode the string into data.
            data = value.encode("utf-8")

            # Get the length of the encoded data.
            data_length = len(data)

            # Pack the length of the data, prefix the
            # string data with it, and return the result.
            return pak.UInt8.pack(data_length, ctx=ctx) + data

.. attention::

    Even though it is *possible* to directly call the ``_unpack`` and ``_pack`` methods of a :class:`.Type`, you should **always** call :meth:`.Type.unpack` and :meth:`.Type.pack` instead.

In the ``_unpack`` method we first unpack the unsigned byte that tells us the length of the string data. Note that we can just pass ``buf`` directly to it; this is because :meth:`.Type.unpack` (and furthermore :meth:`.Packet.unpack`) can accept file objects which contain the raw data. So after the length is unpacked, ``buf`` will have advanced its stream position to the end of the length's data. Next, we read the string data out of ``buf``, and then we decode it using the ``"utf-8"`` codec, and return the result.

In the ``_pack`` method we first encode the string using the ``"utf-8"`` codec to get the string data. Then we get the length of the data, and then pack the length into raw data, tack on the string data to the end of it, and return the result.

Note that when calling :meth:`.Type.unpack` and :meth:`.Type.pack`, we pass the keyword argument ``ctx=ctx``. For now we're going to gloss over exactly why we do this, but know that it is important to forward on the ``ctx`` parameter in this way.

.. note::

    If we wanted to add support for asynchronous unpacking via the :meth:`.Type.unpack_async` method, we could add an override of the :meth:`.Type._unpack_async` method, that would look like this::

        @classmethod
        async def _unpack_async(cls, reader, *, ctx):
            # Unpack the length of the string data.
            data_length = await pak.UInt8.unpack_async(reader, ctx=ctx)

            # Read the string data.
            data = await reader.readexactly(data_length)

            # Decode the data into a string and return it.
            return data.decode("utf-8")

    The ``reader`` parameter here refers to the :class:`asyncio.StreamReader` which contains the raw data. As you can see, the logic is the same as our ``_unpack`` method, only instead utilizing an asynchronous interface.

    Custom types are empowered to neglect to implement either of the unpacking interfaces, since it is very often that they will only need one or the other. This tutorial will carry on with only using the synchronous unpacking interface.

Let's make sure our ``String`` type works as expected:

.. testcode::

    # Length of five, data representing "Hello".
    raw_data = b"\x05Hello"

    value = String.unpack(raw_data)
    print("Value:", repr(value))

    data = String.pack("Hello")
    print("Raw data:", data)

This should then have the output:

.. testoutput::

    Value: 'Hello'
    Raw data: b'\x05Hello'

.. note::

    Pak does provide a :class:`.Type` for a string prefixed by the length of its encoded data: :class:`.PrefixedString`. You could create our ``String`` type by simply doing::

        String = pak.PrefixedString(pak.UInt8)

    However for the purposes of this tutorial, we will be sticking with our custom ``String`` class.

Sending the Strings
*******************

Now we need to figure out how we're gonna use our ``String`` type in a packet. We need to send a reasonably arbitrary amount of URLs in our packet, so how would we do that? Well thankfully, Pak provides :class:`.Array`, a :class:`.Type` which reads contiguous instances of an "element type". For example:

.. testcode::

    import pak

    # An array of two 'UInt8's.
    MyArray = pak.Array(pak.UInt8, 2)

    # Two unsigned bytes with values '1' and '2'.
    raw_data = b"\x01\x02"

    assert MyArray.unpack(raw_data) == [1, 2]

    assert MyArray.pack([1, 2]) == raw_data

However this does not use the more idiomatic syntax for making an :class:`.Array`, using the index operator. For instance, our example of ``pak.Array(pak.UInt8, 2)`` is equivalent to ``pak.UInt8[2]``, and in general ``MyType[size]`` is equivalent to ``pak.Array(MyType, size)``.

But just having a static :class:`int` as the size of the array won't work for us. Luckily, :class:`.Array` can have a :class:`.Type` prefix its data to tell how many elements are in the array. For instance:

.. testcode::

    import pak

    # An array of 'UInt8's prefixed by a 'UInt8'.
    MyPrefixedArray = pak.UInt8[pak.UInt8]

    # An array of length 2 of two unsigned
    # bytes with values '0' and '1'.
    raw_data = b"\x02" + b"\x00\x01"

    assert MyPrefixedArray.unpack(raw_data) == [0, 1]

    assert MyPrefixedArray.pack([0, 1]) == raw_data

So now we can redefine our ``CatPicturesResponse`` packet to be

.. testcode::

    class CatPicturesResponse(pak.Packet):
        cat_pictures: String[pak.UInt16]

It now has the field ``cat_pictures`` which is an array of ``String``\s prefixed by a :class:`.UInt16` size, maintaining the same amount of possible cat pictures as before.

And this does what we expect it to, it works. Well... except for one thing. ``CatPicturesResponse`` no longer has a static size:

.. testcode::

    size = CatPicturesResponse.size()
    print("Size:", size)

This will raise a :exc:`.NoStaticSizeError`:

.. testoutput::

    Traceback (most recent call last):
    ...
    pak.types.type.NoStaticSizeError: 'String[UInt16]' has no static size

This is because our ``String[pak.UInt16]`` type cannot have a size irrespective of any value, because the length of its raw data depends on the length of the to-be-packed list (nor does our ``String`` type have a static size, as the length of its raw data depends on the length of the to-be-packed string). This is an issue for us because our protocol relies on statically sized packets, so that the client and server both know how much data to read, see :ref:`basic-send-receive-packets` from :doc:`basic`.

We can however still get the size of an *instance* of ``CatPicturesResponse``:

.. testcode::

    packet = CatPicturesResponse(cat_pictures=["https://cdn.<...>.com/54028.png"])

    assert packet.size() == 34

----

So how do we fix this? Well, something a lot of packet protocols do is prefix their packet data with the size of the data. We will do this too, prefixing our packet data with a :class:`.UInt8` to tell the size of the packet data.

So let's rewrite our ``read_packet`` and ``write_packet`` functions appropriately::

    def read_packet(packet_cls):
        # Read the data for the size. 'pak.UInt8'
        # has a static size, so we know how much to
        # read beforehand.
        size_data = read_data(pak.UInt8.size())

        # Get the size of the packet so we
        # know how many bytes to read.
        packet_size = pak.UInt8.unpack(size_data)

        # Get the packet data from the client.
        packet_data = read_data(packet_size)

        # Unpack the packet from the data and return it.
        return packet_cls.unpack(packet_data)

    def write_packet(packet):
        # Pack the packet into raw data.
        packet_data = packet.pack()

        # Get the size of the packet and pack it.
        packet_size = len(packet_data)
        size_data   = pak.UInt8.pack(packet_size)

        # Concatenate the size and packet data
        # and send it to the client.
        write_data(size_data + packet_data)

And this works fine, this works great. In ``write_packet`` we end up getting the packet size just from the length of the packed data, but we could've gotten it from using ``packet.size()`` as well.

Now we can finally rewrite our server-side handling code as such::

    # Gets the URLs for cat pictures with a certain fur type.
    def get_cat_picture_urls(fur_type):
        ...

    def handle_request():
        packet = read_packet(CatPicturesRequest)

        if packet.fur_type is pak.Enum.INVALID:
            # If we receive an invalid fur type,
            # report that we have no cat pictures.
            cat_pictures = []

        else:
            cat_pictures = get_cat_picture_urls(packet.fur_type)

        write_packet(
            CatPicturesResponse(cat_pictures=cat_pictures)
        )

Tidying Up
**********

Now that we have this packet data size issue sorted, we can actually modify our ``CatPicturesResponse`` packet slightly:

.. testcode::

    class CatPicturesResponse(pak.Packet):
        cat_pictures: String[None]

Our ``cat_pictures`` field is now a ``String[None]``, which means it is a ``String`` array with no size, reading ``String`` elements until the end of the packet data. This allows us to omit our :class:`.UInt16` length prefix:

.. testcode::

    packet = CatPicturesResponse(
        cat_pictures = [
            "https://cdn.<...>.com/54028.png",
            "https://cdn.<...>.com/28904.png",
        ]
    )

    # Our strings should just be squished up against each other.
    assert packet.pack() == (
        b"\x1fhttps://cdn.<...>.com/54028.png" +
        b"\x1fhttps://cdn.<...>.com/28904.png"
    )

Doing Better: Packet Headers
****************************

The prefixed size of the packet data we added earlier could be considered what is called a "packet header". A packet header is a bit of data that prefixes the main packet data, usually giving information required to marshal the packet data, like what we have with the packet size. Pak has a way of describing this with the class :class:`.Packet.Header`. So how would we go about using this instead of manually using a :class:`.UInt8` size?

Well first, we need to create a parent class for all our protocol's :class:`.Packet`\s. This is needed because our :class:`.Packet.Header` will be prefixing all our packets and we don't want to define a new header for each packet we define. So let's create this base packet::

    import pak

    class FelinePacket(pak.Packet):
        pass

Now we need to give it a packet header. We do so by creating a class named ``Header`` under our ``FelinePacket`` class which inherits from :class:`.Packet.Header`::

    import pak

    class FelinePacket(pak.Packet):
        class Header(pak.Packet.Header):
            pass

And now we need to somehow get our packet size in there. The first thing we need to know is that a :class:`.Packet.Header` is itself a :class:`.Packet` and may have its own fields, same as any other :class:`.Packet`. The second thing we need to know is that each field of the :class:`.Packet.Header` is acquired from the packet for which the header is for, either being acquired by just getting the packet's attribute of the same name as the field, or by calling the method of the same name as the field. Thus we can fill out our header:

.. testcode::

    import pak

    class FelinePacket(pak.Packet):
        class Header(pak.Packet.Header):
            size: pak.UInt8

Our ``FelinePacket.Header`` class will call the :meth:`.Packet.size` method on our ``FelinePacket`` instances to set its ``size`` field. Let's now redefine our previously defined packets, making it so they inherit from ``FelinePacket``:

.. testcode::

    import enum

    class FurType(enum.Enum):
        LongHaired   = 0
        ShortHaired  = 1
        MediumHaired = 2

    class CatPicturesRequest(FelinePacket):
        fur_type: pak.Enum(pak.UInt8, FurType)

    class CatPicturesResponse(FelinePacket):
        cat_pictures: String[None]

Now let's see what the header for these packets would look like, using the :meth:`.Packet.header` method:

.. testcode::

    request = CatPicturesRequest(fur_type=FurType.LongHaired)
    assert request.header() == FelinePacket.Header(size=1)

    response = CatPicturesResponse(cat_pictures=["https://cdn.<...>.com/54028.png"])
    assert response.header() == FelinePacket.Header(size=32)

We should expect the request to have a size of ``1`` and the response to have a size of ``32``.

Now that our packets have a header, their headers automatically get packed together with the normal packet data when using the :meth:`.Packet.pack` method:

.. testcode::

    packet = CatPicturesRequest(fur_type=FurType.MediumHaired)

    assert packet.pack() == b"\x01\x02"

The result of calling ``packet.pack()`` should gives us the header data of ``b"\x01"`` for the size of the packet, packed using a :class:`.UInt8`, squished up next to the normal packet data of ``b"\x02"``.

If you wish to pack a packet without the header, the :meth:`.Packet.pack_without_header` method is available:

.. testcode::

    packet = CatPicturesRequest(fur_type=FurType.MediumHaired)

    assert packet.pack_without_header() == b"\x02"

Calling ``packet.pack_without_header()`` should just give us the normal packet data of ``b"\x02"``.

The behavior of :meth:`.Packet.unpack` however remains unchanged, just unpacking the normal packet data, **not** the header data. This is because the header usually contains the knowledge needed to know how much data to unpack or even what packet should be unpacked in the first place. For unpacking the packet header, you can just unpack it like a normal packet:

.. testcode::

    header_data = b"\x01"

    assert FelinePacket.Header.unpack(header_data) == FelinePacket.Header(size=1)

The header data ``b"\x01"`` should give us a header with its ``size`` field set to ``1``.

----

Now we can rewrite our ``read_packet`` function to use our new packet header::

    def read_packet(packet_cls):
        # Read the data for the header. Our header
        # has a static size, so we know how much to
        # read beforehand.
        header_data = read_data(FelinePacket.Header.size())

        # Unpack the header from the header data.
        header = FelinePacket.Header.unpack(header_data)

        # Get the packet data from the client.
        packet_data = read_data(header.size)

        # Unpack the packet from the data and return it.
        return packet_cls.unpack(packet_data)

We can also rewrite our ``write_packet`` function; in fact we can just revert our previous changes to get our original code back::

    def write_packet(packet):
        # Pack the packet into raw data.
        # This will pack the header as well.
        packet_data = packet.pack()

        # Write the packet data to the client.
        write_data(packet_data)

----

And there we go, we once again have fairly readable and generic code that conforms to our protocol so far. But if we think back to our custom ``String`` type, what was with those mysterious ``ctx`` parameters? They were never quite explained. Move onto :doc:`context` to find out.
