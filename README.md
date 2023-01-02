# Pak

<!-- TODO: Change repo URL and add Python version support badge. -->

[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/friedkeenan/pak.py/ci.yml?label=checks)](https://github.com/friedkeenan/pak.py/commit/HEAD)
[![Read the Docs](https://img.shields.io/readthedocs/pak)](https://pak.readthedocs.io/)
[![Codecov](https://img.shields.io/codecov/c/github/friedkeenan/pak.py)](https://app.codecov.io/gh/friedkeenan/pak.py)
[![License](https://img.shields.io/github/license/friedkeenan/pak.py)](https://github.com/friedkeenan/pak.py/blob/main/LICENSE)

Pak is a simple, yet powerful and extendable Python library for translating between raw data and usable, meaningful values.

Here's an example of simple usage:

```py
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

# Each field will have the appropriate value unpacked from the raw data.
assert packet == MyPacket(
    byte   = 0,
    string = "abcd",
    array  = [1, 2],
)

# Pack the packet into raw data.
packet_data = packet.pack()

# The packed data will be the same as the initial raw data.
assert packet_data == raw_data
```

## Features

- A declarative, simple API for defining packet structures.
- Highly generic, able to fit any packet protocol with relative ease.
- The ability to define your own means of marshaling between raw data and usable values.
- A composable API to allow you to easily leverage pre-existing code and reduce code duplication.
- A healthy set of provided features with general application, such as marshaling numeric, string, and enum values.
- Numerous high quality tests to make sure your code works as expected.
- Well-documented to help you know what APIs exist and how to use them.
- And more!

## Installation

To install Pak, simply install through pip:

> **Warning**
> This is not actually possible at the moment.

```
$ pip install pak
```

## Documentation

The documentation for Pak lives at https://pak.readthedocs.io. There you will find tutorials, including a quickstart, and a reference manual detailing the API that Pak provides.

## Goals

The impetus for creating this library was that I was making a library for the Minecraft networking protocol, which had a very similar API to the one now in Pak. I then wanted to write code for other protocols, and found myself duplicating much of the code I had written for Minecraft's protocol. I therefore created this library so that I did not need to repeat myself for each and every protocol I wrote code for. And so, from that inciting motivation, these are Pak's goals:

- Above all else, maintain a pleasing and readable API.
- Be easily workable with many if not all packet protocols.
- Have a solid base of fundamental or generally applicable features.
- Be easily extendable to account for all the quirks a particular protocol might have.
- Be a venue for me to learn about API design and project maintenance.

In particular Pak's goals do not contain performance. I have not benchmarked the library, and I don't currently intend to go through and make sure all code is optimized, though I of course make no effort to pessimize code either. I may in the future go through and improve the performance of particular features, but in general performance is not something in particular that I strive for.

## Credits

- [ammaraskar/pyCraft](https://github.com/ammaraskar/pyCraft) for my initial inspiration to embark on creating this library and its API, even though it did not result in much resemblance.
- [ManimCommunity/manim](https://github.com/ManimCommunity/manim/) for giving me experience in writing tests and docs and maintaining a serious project.
- [The beginner guide from Write the Docs](https://www.writethedocs.org/guide/writing/beginners-guide-to-docs/) for an excellent walkthrough of good documentation practices.
- The various protocols I stress-tested Pak with to ensure that it is sufficiently generic and easy to use with a wide range of formats. These protocols include but are not limited to [Minecraft](https://www.minecraft.net/), [Transformice](https://www.transformice.com/), and [Super Mario Odyssey Online](https://github.com/CraftyBoss/SuperMarioOdysseyOnline).
