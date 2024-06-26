Adding Some Context
===================

Let us recall the definition of our custom ``String`` type::

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

Where we left it, we were still in the dark about the keyword-only arguments named ``ctx``, just knowing that it's important to forward them on to calls to :meth:`.Type.unpack` and :meth:`.Type.pack`.

The first thing to know is that ``ctx`` is a shortening of the word "context". As its name implies, it provides further context to Pak facilities, such as :meth:`.Type.unpack` and :meth:`.Type.pack`. There are two types of contexts in Pak, one for :class:`.Packet`\s, named :class:`.Packet.Context`, and one for :class:`.Type`\s, named :class:`.Type.Context`.

These contexts contain information that could affect how your protocol works. For instance, it could be that your protocol has multiple "versions" and you're trying to support these different versions at the same time. Let's take our protocol for example: Right now our ``String`` type is prefixed by a :class:`.UInt8` telling the length of the string data, but maybe in a newer version that gets changed so that it's prefixed by a :class:`.UInt16` because we needed longer strings. We would want to be able to use the same ``String`` type everywhere so we don't need to make two different packets with two different string types; contexts allow us to do this. So let's try to model this protocol versioning using contexts.

To start out, we're going to say that the version of our protocol which prefixes string data with a :class:`.UInt8` is version ``0``, and the version which uses a :class:`.UInt16` prefix is version ``1``. Now, we somehow need to bundle this version information into a context. This is done by creating a class named ``Context`` under our ``FelinePacket`` class which inherits from :class:`.Packet.Context`, very similar to how we made a custom :class:`.Packet.Header`::

    import pak

    class FelinePacket(pak.Packet):
        class Context(pak.Packet.Context):
            def __init__(self, *, version=1):
                self.version = version

                super().__init__()

        class Header(pak.Packet.Header):
            size: pak.UInt8

Here we also create the constructor for our context, which takes a keyword-only ``version`` parameter and sets it as an attribute. It also calls the super constructor, which is important.

However, our code as we have it now will raise a :exc:`TypeError`. This is because subclasses of :class:`.Packet.Context` **must** be hashable (mainly for caching purposes). Therefore, we need to provide an implementation of ``__hash__``, and since hashable objects should be equality comparable as well, we'll need to provide an implementation of ``__eq__`` too. Furthermore, hashable objects should also be immutable, and so the constructor of :class:`.Packet.Context` makes it so our context is immutable, and this is why it is important for us to call the super constructor.

So let's add implementations of ``__hash__`` and ``__eq__``:

.. testcode::

    import pak

    class FelinePacket(pak.Packet):
        class Context(pak.Packet.Context):
            def __init__(self, *, version=1):
                self.version = version

                super().__init__()

            def __hash__(self):
                # Our only unique information is our version number.
                return hash(self.version)

            def __eq__(self, other):
                # Our '__eq__' implementation only works with
                # other contexts for 'FelinePacket'.
                if not isinstance(other, FelinePacket.Context):
                    return NotImplemented

                return self.version == other.version

        class Header(pak.Packet.Header):
            size: pak.UInt8

It is somewhat important that our ``FelinePacket.Context`` is default constructible (that we can call it with no arguments), since when no ``ctx`` argument is supplied to operations for ``FelinePacket``, its context will be default constructed and that will be used to supply the extra information to Pak facilities.

----

But how do we pass this information to our ``String`` type? This is where :class:`.Type.Context`\s come in. A :class:`.Type.Context` is basically just a wrapper for :class:`.Packet.Context`\s, giving only the additional information of what :class:`.Packet` the :class:`.Type` operation concerns, if any. A :class:`.Type.Context` can be acquired by calling the :class:`.Type.Context` constructor, optionally passing the relevant :class:`.Packet` instance and :class:`.Packet.Context`. The passed packet can be accessed through the :attr:`~.Type.Context.packet` attribute and the passed context can be accessed through the :attr:`~.Type.Context.packet_ctx` attribute, though you will likely not need to access it through that attribute as the attributes of the :class:`.Packet.Context` can be acquired through the constructed :class:`.Type.Context`, like so:

.. testcode::

    packet_ctx = FelinePacket.Context(version=0)

    type_ctx = pak.Type.Context(ctx=packet_ctx)

    # The 'version' attribute should propagate through 'type_ctx'.
    assert type_ctx.version == 0

:class:`.Type.Context`\s can also be acquired through the :meth:`.Packet.type_ctx` method which will handle supplying the relevant :class:`.Packet` instance for you. Additionally, if you use a :class:`.Type` facility without supplying a :class:`.Type.Context`, a default-constructed :class:`.Type.Context` will be used, containing no real information.

You in all likelihood however will not have to construct a :class:`.Type.Context` yourself. What you *do* need to worry about is supplying appropriate :class:`.Packet.Context`\s to :class:`.Packet` facilities, and Pak will create and pass along the appropriate :class:`.Type.Context` for you.

.. attention::

    It is however **very** important that you pass along these ``ctx`` parameters, as otherwise their contained information will be lost.

.. _versioned-string:

A Versioned String
******************

So let's change our ``String`` type to follow our modified protocol, using a :class:`.UInt8` prefix in protocol version ``0`` and a :class:`.UInt16` in protocol version ``1``. We know now that our implementations of ``_unpack`` and ``_pack`` will be passed an appropriate :class:`.Type.Context` wrapping a provided ``FelinePacket.Context``, so let's start with the barebones::

    import pak

    class String(pak.Type):
        @classmethod
        def _unpack(cls, buf, *, ctx):
            ...

        @classmethod
        def _pack(cls, value, *, ctx):
            ...

We'll be able to access the ``version`` attribute through the ``ctx`` parameter, so we should just be able to change the behavior based on that:

.. testcode::

    import pak

    class String(pak.Type):
        @classmethod
        def _unpack(cls, buf, *, ctx):
            # Unpack the length of the string data.
            if ctx.version < 1:
                data_length = pak.UInt8.unpack(buf, ctx=ctx)
            else:
                data_length = pak.UInt16.unpack(buf, ctx=ctx)

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

            # Pack the length of the data.
            if ctx.version < 1:
                packed_length = pak.UInt8.pack(data_length, ctx=ctx)
            else:
                packed_length = pak.UInt16.pack(data_length, ctx=ctx)

            # Prefix the string data with its length data and return the result.
            return packed_length + data

And that should be it; let's see it in action:

.. testcode::

    # A reminder of our previous definition of this packet.
    class CatPicturesResponse(FelinePacket):
        cat_pictures: String[None]

    ctx_version_0 = FelinePacket.Context(version=0)
    ctx_version_1 = FelinePacket.Context(version=1)

    raw_data_version_0 = b"\x05Hello"
    raw_data_version_1 = b"\x05\x00Hello"

    packet_version_0 = CatPicturesResponse.unpack(raw_data_version_0, ctx=ctx_version_0)
    packet_version_1 = CatPicturesResponse.unpack(raw_data_version_1, ctx=ctx_version_1)

    assert packet_version_0 == packet_version_1 == CatPicturesResponse(cat_pictures=["Hello"])

    assert packet_version_0.pack(ctx=ctx_version_0) == b"\x06\x05Hello"
    assert packet_version_1.pack(ctx=ctx_version_1) == b"\x07\x05\x00Hello"

So there we go, now we have a ``String`` type which packs and unpacks differently based on the version of our protocol.

----

Is there a better way we could do this though? Yes, potentially. What we did is make our ``String`` code explicitly check the version stored in the ``ctx`` parameter, but we could abstract the logic out a bit further into a new :class:`.Type` which would represent the length of our string's encoded data. Then we could just have our ``String`` type call into that, being itself wholly unaware of any protocol versioning. So let's make that :class:`.Type`:

.. testcode::

    class StringDataLength(pak.Type):
        @classmethod
        def _unpack(cls, buf, *, ctx):
            if ctx.version < 1:
                return pak.UInt8.unpack(buf, ctx=ctx)

            return pak.UInt16.unpack(buf, ctx=ctx)

        @classmethod
        def _pack(cls, value, *, ctx):
            if ctx.version < 1:
                return pak.UInt8.pack(value, ctx=ctx)

            return pak.UInt16.pack(value, ctx=ctx)

Pretty simple, right? Let's put it to use now:

.. testcode::

    class String(pak.Type):
        @classmethod
        def _unpack(cls, buf, *, ctx):
            # Unpack the length of the string data.
            data_length = StringDataLength.unpack(buf, ctx=ctx)

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
            return StringDataLength.pack(data_length, ctx=ctx) + data

We've now basically come back to our original ``String`` code, substituting :class:`.UInt8` for our ``StringDataLength`` type. It should work exactly the same as before:

.. testcode::
    :hide:

    class CatPicturesResponse(FelinePacket):
        cat_pictures: String[None]

.. testcode::

    ctx_version_0 = FelinePacket.Context(version=0)
    ctx_version_1 = FelinePacket.Context(version=1)

    raw_data_version_0 = b"\x05Hello"
    raw_data_version_1 = b"\x05\x00Hello"

    packet_version_0 = CatPicturesResponse.unpack(raw_data_version_0, ctx=ctx_version_0)
    packet_version_1 = CatPicturesResponse.unpack(raw_data_version_1, ctx=ctx_version_1)

    assert packet_version_0 == packet_version_1 == CatPicturesResponse(cat_pictures=["Hello"])

    assert packet_version_0.pack(ctx=ctx_version_0) == b"\x06\x05Hello"
    assert packet_version_1.pack(ctx=ctx_version_1) == b"\x07\x05\x00Hello"

We can actually at this point throw out all our custom ``String`` code and just use a :class:`.Type` provided by Pak: :class:`.PrefixedString`. We can simply do

::

    String = pak.PrefixedString(StringDataLength)

and come out with essentially the same functionality. This should give you a good idea about just how modular and composable :class:`.Type`\s can be.

Doing Better: Typelikes
***********************

This is all well and good of course; we're in a pretty good spot with our current definition of ``String``. It's simple and concise, though we *do* have to create a whole new type to handle the version-dependent behavior; that's a little bit of mental overhead. It would be nice if we could just declare it in a nice, simple, declarative way.

This is where the concept of a "typelike" comes in. A typelike is an object that will be converted to a :class:`.Type` in places expecting a :class:`.Type`, such as when defining :class:`.Packet` fields. This of course includes :class:`.Type`\s themselves, since they can be converted to themselves, but the main draw of typelikes is for objects that are *not* :class:`.Type`\s. The only one of these typelikes that Pak provides is ``None``, which will be converted to :class:`.EmptyType`, a type which marshals to and from empty data, useful for "disabling" marshaling in more generic code. You can convert a typelike to a :class:`.Type` by calling :class:`.Type`, passing the typelike, like so:

.. testcode::

    assert pak.Type(None) is pak.EmptyType

----

But why are typelikes relevant here and how can we add our own?

Well, it would be really nice if instead of creating a whole ``StringDataLength`` type to handle the different protocol versions, we could instead have something like this::

    String = pak.PrefixedString({
        0: pak.UInt8,
        1: pak.UInt16,
    })

This would be much more declarative, showing us very clearly that in version ``0``, strings are prefixed with a :class:`.UInt8` and in version ``1`` with a :class:`.UInt16`. This is where typelikes would help us, as we could make it so :class:`dict`\s are typelike, converting to a special type that forwards onto other types depending on the protocol version. Now, how would we go about this?

First, we'll create the forwarding type; let's call it ``VersionedType``::

    class VersionedType(pak.Type):
        # This will eventually be filled in with a specified dictionary.
        version_types = None

        @classmethod
        def appropriate_type(cls, *, ctx):
            # Get the appropriate type for the version, converting any typelike results.
            return pak.Type(cls.version_types[ctx.version])

        @classmethod
        def _unpack(cls, buf, *, ctx):
            return cls.appropriate_type(ctx=ctx).unpack(buf, ctx=ctx)

        @classmethod
        def _pack(cls, value, *, ctx):
            return cls.appropriate_type(ctx=ctx).pack(value, ctx=ctx)

And it's basically as simple as that. In a real protocol where you're gonna have more than two protocol versions, you would want a more refined way of getting the appropriate type than just indexing directly into the dictionary, but this is fine for our purposes. In the real world, you would also want to forward on more aspects of :class:`.Type`\s, but what we've done is sufficient for a tutorial.

Now how do we fill in that ``version_types`` attribute? Well, we can make it so calling ``VersionedType`` will fill it in, meaning we could use ``VersionedType`` like so::

    VersionedType({
        0: pak.UInt8,
        1: pak.UInt16,
    })

This would be in line with how for example :class:`.Enum` is used. So how do we do that?

Well, when :class:`.Type`\s get called, the :meth:`.Type._call` classmethod gets called. This is done to avoid having to mess with the ``__new__`` method and making sure that calling a :class:`.Type` is conceptually separated from constructing a :class:`.Type`. From the ``_call`` method we can return a new subclass of ``VersionedType`` which has its ``version_types`` attribute filled in, using the helper method :meth:`.Type.make_type`:

.. testcode::

    class VersionedType(pak.Type):
        # This will eventually be filled in with a specified dictionary.
        version_types = None

        @classmethod
        def appropriate_type(cls, *, ctx):
            # Get the appropriate type for the version, converting any typelike results.
            return pak.Type(cls.version_types[ctx.version])

        @classmethod
        def _unpack(cls, buf, *, ctx):
            return cls.appropriate_type(ctx=ctx).unpack(buf, ctx=ctx)

        @classmethod
        def _pack(cls, value, *, ctx):
            return cls.appropriate_type(ctx=ctx).pack(value, ctx=ctx)

        @classmethod
        def _call(cls, version_types):
            # Make a subclass with the same name and with the 'version_types' attribute set.
            return cls.make_type(
                cls.__name__,

                version_types = version_types
            )

We should now be able to use it like so:

.. testcode::

    StringDataLength = VersionedType({
        0: pak.UInt8,
        1: pak.UInt16,
    })

    ctx_version_0 = pak.Type.Context(ctx=FelinePacket.Context(version=0))
    ctx_version_1 = pak.Type.Context(ctx=FelinePacket.Context(version=1))

    raw_data_version_0 = b"\x02"
    raw_data_version_1 = b"\x02\x00"

    value_version_0 = StringDataLength.unpack(raw_data_version_0, ctx=ctx_version_0)
    value_version_1 = StringDataLength.unpack(raw_data_version_1, ctx=ctx_version_1)

    assert value_version_0 == value_version_1 == 2

    assert StringDataLength.pack(2, ctx=ctx_version_0) == raw_data_version_0
    assert StringDataLength.pack(2, ctx=ctx_version_1) == raw_data_version_1

And that's great, but we still haven't gotten to the API we set out for. To get there, we'll need to make :class:`dict`\s into typelikes that convert into a ``VersionedType``. To do this, we can use :meth:`.Type.register_typelike`, passing it the class of objects we want to be typelike (:class:`dict`), and a callable that will convert a :class:`dict` into a ``VersionedType``. Luckily, we just turned ``VersionedType`` into just that::

    pak.Type.register_typelike(dict, VersionedType)

And with that, we can finally get our desired API::

    String = pak.PrefixedString({
        0: pak.UInt8,
        1: pak.UInt16,
    })

----

So there we go, we're now left with this code defining our current protocol::

    import enum
    import pak

    class FelinePacket(pak.Packet):
        class Context(pak.Packet.Context):
            def __init__(self, *, version=1):
                self.version = version

                super().__init__()

            def __hash__(self):
                # Our only unique information is our version number.
                return hash(self.version)

            def __eq__(self, other):
                # Our '__eq__' implementation only works with
                # other contexts for 'FelinePacket'.
                if not isinstance(other, FelinePacket.Context):
                    return NotImplemented

                return self.version == other.version

        class Header(pak.Packet.Header):
            size: pak.UInt8

    String = pak.PrefixedString({
        0: pak.UInt8,
        1: pak.UInt16,
    })

    class FurType(enum.Enum):
        LongHaired   = 0
        ShortHaired  = 1
        MediumHaired = 2

    class CatPicturesRequest(FelinePacket):
        fur_type: pak.Enum(pak.UInt8, FurType)

    class CatPicturesResponse(FelinePacket):
        cat_pictures: String[None]

But what if our protocol became a little more complicated, where we didn't know ahead of time which packet we were receiving? How would we read a packet without knowing which :class:`.Packet` subclass to use? We can move on to :doc:`identifying` to find out.
