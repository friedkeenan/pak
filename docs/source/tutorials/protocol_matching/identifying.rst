An Identifying Protocol
=======================

So where we left off in :doc:`context`, we were left with the following packets::

    import enum
    import pak

    class FelinePacket(pak.Packet):
        class Context(pak.Packet.Context):
            ...

        class Header(pak.Packet.Header):
            size: pak.UInt8

    String = pak.PrefixedString({
        0: pak.UInt8,
        1: pak.Uint16
    })

    class FurType(enum.Enum):
        LongHaired   = 0
        ShortHaired  = 1
        MediumHaired = 2

    class CatPicturesRequest(FelinePacket):
        fur_type: pak.Enum(pak.UInt8, FurType)

    class CatPicturesResponse(FelinePacket):
        cat_pictures: String[None]

And we read these packets by passing them to ``read_packet``, like so::

    packet = read_packet(CatPicturesRequest)

But with many packet protocols, you simply don't know what packet you're going to be sent next, so something like ``read_packet(CatPicturesRequest)`` isn't applicable. So what do these protocols look like?

Well, packets in this sort of protocol almost always have some sort of "ID" that identifies what kind of packet it is. This ID could be sent in any sort of way, but it tends to live in the packet header, like the size of a packet might. So how would our protocol look if it were like this?

----

Instead of the client asking the server for URLs to pictures of cats with a certain fur type, the client will send a packet asking the server for a list of numbers that correspond to certain cats with a certain fur type. We will call these numbers "cat IDs" and they will be represented by a :class:`.UInt16`. The client can then send a different packet, bundling a single cat ID, asking for further information about the corresponding cat, namely its birth date and a URL to a picture of the cat.

Let's mock these packets up::

    class CatIDsRequest(FelinePacket):
        fur_type: pak.Enum(pak.UInt8, FurType)

    class CatIDsResponse(FelinePacket):
        fur_type: pak.Enum(pak.UInt8, FurType)
        cat_ids:  pak.UInt16[None]

    class CatInfoRequest(FelinePacket):
        cat_id: pak.UInt16

    class CatInfoResponse(FelinePacket):
        cat_id:      pak.UInt16
        picture_url: String

        # The cat's birth date is represented by
        # a 'UInt16' for the year, a 'UInt8' for
        # the month, and a 'UInt8' for the day.

        birth_year:  pak.UInt16
        birth_month: pak.UInt8
        birth_day:   pak.UInt8

It's unknown which packet will be received ahead of time, as the client can send a ``CatIDsRequest`` or ``CatInfoRequest`` packet at any time, and the server can similarly send a ``CatIDsResponse`` or ``CatInfoResponse`` packet at any time. Therefore, each packet will have a :class:`.UInt8` in its header, situated before the packet size, which will correspond to which packet is being received. This number is called the "packet ID". The packet IDs for ``CatIDsRequest`` and ``CatInfoRequest`` will be ``0`` and ``1`` respectively, and ``CatIDsResponse`` and ``CatInfoResponse`` will similarly have IDs of ``0`` and ``1`` respectively.

So how would we use Pak to implement this protocol? First, we should look at the classmethod :meth:`.Packet.id`. This method can optionally take in a :class:`.Packet.Context` parameter, and returns the ID of the packet. If there is no ID, then the method returns ``None``; by default, :class:`.Packet`\s have no ID. We can override this method to set the packet IDs, like so:

.. testcode::
    :hide:

    import enum
    import pak

    class FelinePacket(pak.Packet):
        class Header(pak.Packet.Header):
            id:   pak.UInt8
            size: pak.UInt8

        class Context(pak.Packet.Context):
            def __init__(self, *, version=1):
                self.version = version

                super().__init__()

            def __hash__(self):
                return hash(self.version)

            def __eq__(self, other):
                if not isinstance(other, FelinePacket.Context):
                    return NotImplemented

                return self.version == other.version

    # This isn't really what our 'String' type looked like,
    # but it's how it looked in protocol version 1.
    String = pak.PrefixedString(pak.UInt16)

    class FurType(enum.Enum):
        LongHaired   = 0
        ShortHaired  = 1
        MediumHaired = 2

.. testcode::

    class CatIDsRequest(FelinePacket):
        fur_type: pak.Enum(pak.UInt8, FurType)

        @classmethod
        def id(cls, *, ctx):
            return 0

We can then test it out:

.. testcode::

    print("Packet ID:", CatIDsRequest.id())

This will spit out ``0``:

.. testoutput::

    Packet ID: 0

Note that we did not need to specify the ``ctx`` parameter despite not defaulting it in our overriding of the ``id`` method. This is because Pak will handle the ``ctx`` parameter being unspecified for you, always passing you a proper :class:`.Packet.Context`.

Cool, so now our ``CatIDsRequest`` packet has an ID. How do we get that into the header? Basically the same way we got the packet size into the header in :doc:`stringy`::

    class FelinePacket(pak.Packet):
        class Header(pak.Packet.Header):
            id:   pak.UInt8
            size: pak.UInt8

        class Context(pak.Packet.Context):
            ...

We added the ``id`` field to our packet header, before the ``size`` field as described earlier. The :class:`.Packet.Header` machinery will call the :meth:`.Packet.id` method (with an appropriate :class:`.Packet.Context`) and put it in the header:

.. testcode::

    packet = CatIDsRequest(fur_type=FurType.MediumHaired)

    print("Packet header:", packet.header())
    print("Raw data:",      packet.pack())

This will give us the following output:

.. testoutput::

    Packet header: FelinePacket.Header(id=0, size=1)
    Raw data: b'\x00\x01\x02'

In the raw data, the ``\x00`` represents the packet ID, the ``\x01`` represents the size of the packet body, and ``\x02`` represents the fur type ``FurType.MediumHaired``.

Cool, so now we know how to add packet IDs. But it is a bit *much* that we have to define a whole classmethod to simply have an ID of ``0``. It's not too much for one or a few packets, but it would add up for a full fledged protocol. We're not even touching the ``ctx`` parameter; we're not doing any real work at all. Luckily for us though, Pak alleviates this concern. We can simply set the ID like so:

.. testcode::

    class CatIDsRequest(FelinePacket):
        id = 0

        fur_type: pak.Enum(pak.UInt8, FurType)

Pak will transform our simply setting the ``id`` attribute so that you still call the :meth:`.Packet.id` method like normal; the interface stays the same:

.. testcode::

    print("CatIDsRequest ID:", CatIDsRequest.id())

This will work the same as it did with our classmethod:

.. testoutput::

    CatIDsRequest ID: 0

Sending and Receiving Unknown Packets
*************************************

Let's fill out the IDs on all of our packets now::

    class CatIDsRequest(FelinePacket):
        id = 0

        fur_type: pak.Enum(pak.UInt8, FurType)

    class CatIDsResponse(FelinePacket):
        id = 0

        fur_type: pak.Enum(pak.UInt8, FurType)
        cat_ids:  pak.UInt16[None]

    class CatInfoRequest(FelinePacket):
        id = 1

        cat_id: pak.UInt16

    class CatInfoResponse(FelinePacket):
        id = 1

        cat_id:      pak.UInt16
        picture_url: String

        # The cat's birth date is represented by
        # a 'UInt16' for the year, a 'UInt8' for
        # the month, and a 'UInt8' for the day.

        birth_year:  pak.UInt16
        birth_month: pak.UInt8
        birth_day:   pak.UInt8

That packets have the same ID as another may seem like an issue at first, after all the ID is meant to uniquely identify which packet is being received, but it's actually okay since in each pair of packets with the same ID, one is received by the client, and one is received by the server; therefore each received type of packet has a unique ID. Packets bound to the client have unique IDs among clientbound packets, and packets bound to the server have unique IDs among serverbound packets.

Finally now we can worry about how we actually send and receive these packets. Sending them is easy, so we'll start with that. Here's our ``write_packet`` function from previous sections::

    def write_packet(packet):
        # Pack the packet into raw data.
        # This will pack the header as well.
        packet_data = packet.pack()

        # Write the packet data to the client.
        write_data(packet_data)

And... that's it. We don't have to change anything. The header machinery takes care of prefixing the data with the packet ID for us. Nice. So how about receiving packets? Well here's our previous ``read_packet`` function::

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

We'll have to change this in a couple ways. First of all, our previous function takes in a ``packet_cls`` parameter to know which :class:`.Packet` to unpack. This doesn't work for us anymore as we don't know which :class:`.Packet` we're receiving beforehand. Therefore we'll need to get rid of the parameter entirely, and figure out which class to use based on the packet ID contained in the header. Let's see what that looks like::

    def read_packet():
        # Read the data for the header. Our header
        # has a static size, so we know how much to
        # read beforehand.
        header_data = read_data(FelinePacket.Header.size())

        header = FelinePacket.Header.unpack(header_data)

        # Set 'packet_cls' based on the ID in the header.
        #
        # We only have to worry about serverbound packets
        # since we are playing the part of the server in
        # our protocol.
        if header.id == 0:
            packet_cls = CatIDsRequest
        elif header.id == 1:
            packet_cls = CatInfoRequest
        else:
            # There are other ways to handle unknown
            # packets, but here we will raise an error.
            raise ValueError("Invalid packet ID")

        # Get the packet data from the client.
        packet_data = read_data(header.size)

        # Unpack the packet from the data and return it.
        return packet_cls.unpack(packet_data)

First we unpack the header like before. Then we use the ``id`` attribute of the header to see which packet we're receiving, stored in ``packet_cls``. If we don't recognize the ID, we raise a :exc:`ValueError`. Then we read the packet data and unpack it like before.

.. note::

    Best practice would involve passing a :class:`.Packet.Context` to the :class:`.Packet` operations we use. We neglect to do so here for the sake of tutorial code.

There is a part that's kind of subpar though, our whole ``if``/``elif`` chain in there. It's not very scalable, and it requires two completely separate sources of truth; there's the ID specified in the packet definition and then the ID specified in our ``read_packet`` function. We could *maybe* alleviate that by doing ``== CatIDsRequest.id()`` instead of ``== 0`` which *would* be an improvement, but then we're still defining what packets exist and what packets can be received in two separate places. If we add a new packet, we need to add it in two places: its class definition, and here in our ``read_packet`` function.

Thankfully, Pak addresses this issue for us, with the :meth:`.Packet.subclass_with_id` classmethod. With it we can ask for a subclass of our main :class:`.Packet` class, ``FelinePacket``, which has the appropriate ID, allowing us to have a single sourch of truth: our packet definitions. But here's the sticking point: the way we have our classes set up right now, we have multiple subclasses with the same ID. This wasn't a problem before because the packet IDs are unique within their serverbound/clientbound set of packets, and we were just manually checking the IDs. We can alleviate this issue by fiddling with our inheritance tree a bit though:

.. testcode::

    class ServerboundFelinePacket(FelinePacket):
        pass

    class ClientboundFelinePacket(FelinePacket):
        pass

Here we define two new classes, ``ServerboundFelinePacket`` and ``ClientboundFelinePacket``. Their class definitions are empty, as they only exist to separate serverbound and clientbound packets in our inheritance tree. Then we can make our actual packets inherit from the correct class:

.. testcode::

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

Now every ``ServerboundFelinePacket`` and every ``ClientboundFelinePacket`` have a unique ID. So let's test out :meth:`.Packet.subclass_with_id`:

.. testcode::

    print("Serverbound ID 0:", ServerboundFelinePacket.subclass_with_id(0).__qualname__)

Since ``CatIDsRequest`` is the serverbound packet with ID ``0``, we should get the following output:

.. testoutput::

    Serverbound ID 0: CatIDsRequest

Cool. But what if we were to pass an ID that doesn't correspond to any packet? In that case, :meth:`.Packet.subclass_with_id` will return ``None``. So, armed with this new tool, let's rewrite our ``read_packet`` function::

    def read_packet():
        # Read the data for the header. Our header
        # has a static size, so we know how much to
        # read beforehand.
        header_data = read_data(FelinePacket.Header.size())

        header = FelinePacket.Header.unpack(header_data)

        # Set 'packet_cls' based on the ID in the header.
        #
        # We only have to worry about serverbound packets
        # since we are playing the part of the server in
        # our protocol.
        packet_cls = ServerboundFelinePacket.subclass_with_id(header.id)
        if packet_cls is None:
            # There are other ways to handle unknown
            # packets, but here we will raise an error.
            raise ValueError("Invalid packet ID")

        # Get the packet data from the client.
        packet_data = read_data(header.size)

        # Unpack the packet from the data and return it.
        return packet_cls.unpack(packet_data)

We were able to get rid of our ``if``/``elif`` chain and replace it with a much simpler call to :meth:`.Packet.subclass_with_id`, resulting in what I would say is much nicer code.

Versioned Packet IDs
********************

In the previous :doc:`context` section, we explored how our ``String`` type could change how it marshals to and from raw data based on the version of our protocol. Similarly, packet IDs can change can change their value based on our protocol version. So how would we go about handling that?

Well, if we recall, when we overrode the :meth:`.Packet.id` classmethod, we had a ``ctx`` parameter available to us. This ``ctx`` parameter will name an appropriate :class:`.Packet.Context`, in this case our ``FelinePacket.Context``, which will contain a ``version`` attribute telling us our protocol version. So let's say that in protocol version ``0``, our packet IDs are as they are now, but in version ``1``, they're swapped, so that ``CatIDsRequest`` and ``CatIDsResponse`` have ID ``1`` and ``CatInfoRequest`` and ``CatInfoResponse`` have ID ``0``. Let's see how we could model this::

    class CatIDsRequest(ServerboundFelinePacket):
        @classmethod
        def id(cls, *, ctx):
            if ctx.version < 1:
                return 0

            return 1

        fur_type: pak.Enum(pak.UInt8, FurType)

    class CatIDsResponse(ClientboundFelinePacket):
        @classmethod
        def id(cls, *, ctx):
            if ctx.version < 1:
                return 0

            return 1

        fur_type: pak.Enum(pak.UInt8, FurType)
        cat_ids:  pak.UInt16[None]

    class CatInfoRequest(ServerboundFelinePacket):
        @classmethod
        def id(cls, *, ctx):
            if ctx.version < 1:
                return 1

            return 0

        cat_id: pak.UInt16

    class CatInfoResponse(ClientboundFelinePacket):
        @classmethod
        def id(cls, *, ctx):
            if ctx.version < 1:
                return 1

            return 0

        cat_id:      pak.UInt16
        picture_url: String

        # The cat's birth date is represented by
        # a 'UInt16' for the year, a 'UInt8' for
        # the month, and a 'UInt8' for the day.

        birth_year:  pak.UInt16
        birth_month: pak.UInt8
        birth_day:   pak.UInt8

Here we replaced all our previous lines which simply set the ``id`` attribute to a number with full-fledged classmethods, returning a different number depending on ``ctx.version``. And well, this *works*, and it's *mostly* clear what's going on, but it's also not as clear as what we had before, with simply setting the ``id`` attribute to a number. It's less declarative, more imperative.

If you'll recall, we had a similar situation in :ref:`versioned-string`. The code we had for changing how strings were marshaled depending on the protocol version was also more imperative than declarative, and wasn't super readable. We solved this issue by introducing the concept of typelikes, and registered :class:`dict`\s as typelike, resulting in an API that allowed us to define our ``String`` type like so::

    String = pak.PrefixedString({
        0: pak.UInt8,
        1: pak.UInt16,
    })

This was decently more declarative and readable than what we had before. Maybe we can have a similar API for packet IDs?

Doing Better: Dynamic Values
****************************

In fact, we *can* have a similar API for packet IDs! In the end, we'll be able to define IDs like this::

    class CatInfoRequest(ServerboundFelinePacket):
        id = {
            0: 0,
            1: 1,
        }

        cat_id: pak.UInt16

So how do we get there? Pak provides a utility for this issue: :class:`.DynamicValue`. This is used to transform one value into a classmethod-ish thing, which can provide different "return" values based on a ``ctx`` parameter and the initial value for the :class:`.DynamicValue`. :class:`.Packet` will automatically try to make the ``id`` attribute we set into a :class:`.DynamicValue`. So for us, we want to make it so :class:`dict`\s will get enrolled in this machinery, and return the appropriate ID values based on our protocol version. Let's walk through it::

    class VersionedDynamicValue(pak.DynamicValue):
        ...

First we create a class which inherits from :class:`.DynamicValue` named ``VersionedDynamicValue``. This is what will be instantiated when things like :class:`.Packet` interact with the :class:`.DynamicValue` machinery.

::

    class VersionedDynamicValue(pak.DynamicValue):
        _type = dict

        ...

Next we set the ``_type`` attribute to the :class:`dict` type so that instances of :class:`dict` will be changed into a ``VersionedDynamicValue``.

::

    class VersionedDynamicValue(pak.DynamicValue):
        _type = dict

        def __init__(self, initial_value):
            self.version_info = initial_value

        ...

Now we add an ``__init__`` method which accepts an ``initial_value`` parameter which names the initial :class:`dict` value for our ``VersionedDynamicValue``, which we then store in the ``version_info`` attribute.

.. testcode::

    class VersionedDynamicValue(pak.DynamicValue):
        _type = dict

        def __init__(self, initial_value):
            self.version_info = initial_value

        def get(self, *, ctx=None):
            return self.version_info[ctx.version]

Finally we add the ``get`` method, which accepts a ``ctx`` parameter that will name either an appropriate :class:`.Packet.Context` or an appropriate :class:`.Type.Context`, or ``None``. In this method we return the appropriate value based on the protocol version stored within the ``ctx`` parameter.

So let's try this puppy out:

.. testcode::

    class CatIDsRequest(ServerboundFelinePacket):
        id = {
            0: 0,
            1: 1,
        }

        fur_type: pak.Enum(pak.UInt8, FurType)

    ctx_version_0 = FelinePacket.Context(version=0)
    ctx_version_1 = FelinePacket.Context(version=1)

    print("Version 0 ID:", CatIDsRequest.id(ctx=ctx_version_0))
    print("Version 1 ID:", CatIDsRequest.id(ctx=ctx_version_1))

If we did everything right, we should get the following output:

.. testoutput::

    Version 0 ID: 0
    Version 1 ID: 1

----

Pretty swanky I'd say. We got to keep a declarative API, and have it similar to the typelike API we made in :doc:`context`. But how would we go about handling all these packets, especially at scale? Let's head onto :doc:`handle` to find out.
