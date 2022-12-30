Pak: A General Purpose Packet Marshaling Library
===========================================================

**Pak** is a simple, yet powerful and extendable Python library
for translating between raw data and usable, meaningful values.

----

An example of simple usage:

.. testcode::

    import pak

    raw_data = (
        # Represents the value '0'.
        b"\x00" +

        # A string encoded in 4 bytes, with characters "abcd".
        b"\x04" + b"abcd" +

        # Two contiguous 16-bit, little endian numbers, '1' and '2'.
        b"\x01\x00" + b"\x02\x00"
    )

    class MyPacket(pak.Packet):
        byte:   pak.Int8
        string: pak.PrefixedString(pak.UInt8)
        array:  pak.UInt16[2]

    # Unpack a packet from the raw data.
    packet = MyPacket.unpack(raw_data)

    print("Packet:", packet)

    # Pack the packet into raw data.
    packet_data = packet.pack()

    print("Packet data:", packet_data)

Output:

.. testoutput::

    Packet: MyPacket(byte=0, string='abcd', array=[1, 2])
    Packet data: b'\x00\x04abcd\x01\x00\x02\x00'

Features
********

- A declarative, simple API for defining packet structures.
- Highly generic, able to fit any packet protocol with relative ease.
- The ability to define your own means of marshaling between raw data and usable values.
- A composable API to allow you to easily leverage pre-existing code and reduce code duplication.
- A healthy set of provided features with general application, such as marshaling numeric, string, and enum values.
- Numerous high quality tests to make sure your code works as expected.
- Well-documented to help you know what APIs exist and how to use them.
- And more!

Table of Contents
*****************

.. toctree::
    :maxdepth: 2

    tutorials
    reference


Indices and Tables
******************

- :ref:`genindex`
- :ref:`modindex`
- :ref:`search`
