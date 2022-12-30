Quickstart
==========

This document should introduce you to how to get started with Pak, giving you a broad-strokes understanding of how the library functions.

Installation
************

.. TODO: This may need to be changed to 'pak.py' depending on pypi.

To install Pak, simply install through pip:

.. attention::

    This is not actually possible at the moment.

::

    $ pip install pak

Defining a Packet
*****************

A packet is a collection of values that may be marshaled to and from raw data. This concept is modeled in Pak by the :class:`.Packet` class.

Let's see how to define our own packet::

    import pak

    class MyPacket(pak.Packet):
        field: pak.Int8

First, we import ``pak`` to access the library. Then, we create the class ``MyPacket``, which inherits from the :class:`.Packet` class. Within the definition of the ``MyPacket`` class, we add a class annotation with the name ``field`` and the annotation :class:`.Int8`. This defines that ``MyPacket`` has a field named ``field`` which is marshaled according to :class:`.Int8`. We'll get more into what exactly :class:`.Int8` represents later.

So, let's see how to use our newly defined packet:


.. testcode::

    import pak

    class MyPacket(pak.Packet):
        field: pak.Int8

    packet = MyPacket(field=1)

    data_from_packet = packet.pack()
    print("Raw data:", data_from_packet)

    packet_from_data = MyPacket.unpack(b"\x01")
    print("Field value:", packet_from_data.field)

First, we create ``packet`` by calling the constructor and passing ``field=1``, setting that field to the value ``1``. Next we call the :meth:`.Packet.pack` method to marshal ``packet`` to ``data_from_packet``, and then print it.

Separately from that, we call the :meth:`.Packet.unpack` class method to marshal ``b"\x01"`` to ``packet_from_data``, and then print the resulting value of ``packet_from_data.field``.

Thus, you should get the following output:

.. testoutput::

    Raw data: b'\x01'
    Field value: 1

You can add additional fields by adding more annotations:

.. testcode::

    import pak

    class MyPacket(pak.Packet):
        field:     pak.Int8
        new_field: pak.Int8

    packet = MyPacket.unpack(b"\x01\x02")
    print(packet)

With this we have a second field in ``MyPacket`` creatively named ``new_field``. This field will correspond to raw data directly after the raw data of the first field. So then we unpack the raw data ``b"\x01\x02\x00"`` and print the resulting packet:

.. testoutput::

    MyPacket(field=1, new_field=2)

Field Types
***********

But what exactly are those :class:`.Int8` annotations doing?

:class:`.Int8` is referred to as the "type" of a packet field, and, as mentioned previously, they define how each field gets marshaled to and from raw bytes. This concept is modeled in Pak by the :class:`.Type` class. Pak comes with a healthy set of provided :class:`.Type`\s, which you can browse at the :ref:`Types reference <reference-types>`.

The main difference between a :class:`.Packet` and a :class:`.Type` is that :class:`.Packet`\s contain values, while :class:`.Type`\s only define how to marshal values to and from raw data; they don't hold any value themselves.

Let's see how to use a :class:`.Type`:

.. testcode::

    import pak

    data_from_value = pak.Int8.pack(1)
    print("Raw data:", data_from_value)

    value_from_data = pak.Int8.unpack(b"\x01")
    print("Value:", value_from_data)

First we call the :meth:`.Type.pack` method to get the raw data which corresponds to the value ``1``, printing the result. Then we call the :meth:`.Type.unpack` method to get the value which corresponds to the raw data ``b"\x01"``, printing the result.

We then should expect the following output:

.. testoutput::

    Raw data: b'\x01'
    Value: 1

----

:class:`.Type`\s may also have default values:

.. testcode::

    import pak

    default_value = pak.Int8.default()
    print("Default:", default_value)

Here we call the :meth:`.Type.default` method and print the result:

.. testoutput::

    Default: 0

This default value will be used when constructing :class:`.Packet`\s if no other value is provided for the field:

.. testcode::

    import pak

    class MyPacket(pak.Packet):
        field: pak.Int8

    print(MyPacket())

Since we supplied no value for ``field``, the default value of ``0`` will be used:

.. testoutput::

    MyPacket(field=0)

Keep in mind however that not all :class:`.Type`\s have default values, though many do.

----

:class:`.Type`\s have sizes as well, measuring how many raw bytes values get packed into:

.. testcode::

    import pak

    data_size = pak.Int8.size(2)
    print("Size:", data_size)

Here we call the :meth:`.Type.size` method to get the size of the raw data that corresponds to the value ``2``, and print the result:

.. testoutput::

    Size: 1

In the worst case, determining the size of a :class:`.Type` will perform as badly as packing the value and getting the length of the resulting data, however this may often be optimized by the :class:`.Type`. In fact in some cases you can get the size of a :class:`.Type` irrespective of any value:

.. testcode::

    import pak

    data_size = pak.Int8.size()
    print("Size:", data_size)

Here we omit passing any value to the :meth:`.Type.size` method in order to get the "static" size of the :class:`.Type`:

.. testoutput::

    Size: 1

You can also get the size of :class:`.Packet`\s, like so:

.. testcode::

    import pak

    class MyPacket(pak.Packet):
        field: pak.Int8

    packet_size = MyPacket().size()
    print("Packet size:", packet_size)

We call the :meth:`.Packet.size` method on an instance of ``MyPacket``, which will use the sizes of its field :class:`.Type`\s and the values of its fields to calculate the total size:

.. testoutput::

    Packet size: 1

You may in certain cases be able to get the static size of a :class:`.Packet` irrespective of the values of its fields:

.. testcode::

    import pak

    class MyPacket(pak.Packet):
        field: pak.Int8

    packet_size = MyPacket.size()
    print("Packet size:", packet_size)

Here we call the :meth:`.Packet.size` method on the ``MyPacket`` *class* to get its static size:

.. testoutput::

    Packet size: 1

The Next Step
*************

Now you should have a decent understanding of the basics of the library. To increase the depth of your understanding, going through :doc:`protocol_matching/index` may be helpful.
