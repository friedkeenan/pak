import pak
import pytest

def test_static_string():
    TestString = pak.StaticString(4)

    pak.test.type_behavior(
        TestString,

        ("abc", b"abc\x00"),
        ("ab",  b"ab\x00\x00"),
        ("a",   b"a\x00\x00\x00"),
        ("",    b"\x00\x00\x00\x00"),

        ("\u200B", b"\xE2\x80\x8B\x00"),

        static_size = 4,
        alignment   = 1,
        default     = "",
    )

    assert TestString.unpack(b"\xFF\x00\x00\x00") == "\uFFFD"

    with pytest.raises(ValueError, match="null terminator"):
        TestString.unpack(b"abcd")

    with pytest.raises(ValueError, match="too large"):
        TestString.pack("abcd")

    # Make sure we don't just raise an error when the string
    # is too long but rather when the packed data would be
    # too large.
    with pytest.raises(ValueError, match="too large"):
        TestString.pack("\u200B\u200B")

def test_prefixed_string():
    TestPrefixed = pak.PrefixedString(pak.UInt8)

    pak.test.type_behavior(
        TestPrefixed,

        ("abc", b"\x03abc"),
        ("ab",  b"\x02ab"),
        ("a",   b"\x01a"),
        ("",    b"\x00"),

        ("\u200B", b"\x03\xE2\x80\x8B"),

        static_size = None,
        default     = "",
    )

    assert TestPrefixed.unpack(b"\x01\xFF") == "\uFFFD"

def test_char():
    pak.test.type_behavior(
        pak.Char,

        ("h", b"h"),

        static_size = 1,
        alignment   = 1,
        default     = "a"
    )

    assert pak.Char.pack("Hello") == b"H"

    with pytest.raises(UnicodeDecodeError, match="codec can't decode byte"):
        pak.Char.unpack(b"\x80")

    with pytest.raises(UnicodeEncodeError, match="codec can't encode character"):
        pak.Char.pack("\x80")

    with pytest.raises(pak.util.BufferOutOfDataError):
        pak.Char.unpack(b"")

    Utf8Char = pak.Char("utf-8")
    pak.test.type_behavior(
        Utf8Char,

        ("h",    b"h"),
        ("\x80", b"\xC2\x80"),

        static_size = None,
        default     = "a",
    )

def test_char_array():
    assert isinstance(pak.Char[1].unpack(b"a"), str)

    pak.test.type_behavior(
        pak.Char[2],

        ("ab", b"ab"),

        static_size = 2,
        alignment   = 1,
        default     = "aa",
    )

    pak.test.type_behavior(
        pak.Char[pak.Int8],

        ("ab", b"\x02ab"),
        ("",   b"\x00"),

        static_size = None,
        default     = "",
    )

    pak.test.type_behavior(
        pak.Char[None],

        ("abc", b"abc"),

        static_size = None,
        default     = "",
    )

    class TestAttr(pak.Packet):
        test:  pak.Int8
        array: pak.Char["test"]

    assert TestAttr(test=2).array == "aa"

    pak.test.packet_behavior(
        (TestAttr(test=2, array="ab"), b"\x02ab"),
    )

    ctx_len_2 = TestAttr(test=2, array="ab").type_ctx(None)
    pak.test.type_behavior(
        pak.Char["test"],

        ("ab", b"ab"),

        static_size = 2,
        alignment   = 1,
        default     = "aa",
        ctx         = ctx_len_2,
    )

    assert pak.Char[2].pack("abc")           == b"ab"
    assert pak.Char[2].pack("a")             == b"aa"
    assert pak.Char[pak.Int8].unpack(b"\x02abc") ==  "ab"

    with pytest.raises(pak.util.BufferOutOfDataError):
        pak.Char[2].unpack(b"a")

    with pytest.raises(pak.util.BufferOutOfDataError):
        pak.Char[pak.Int8].unpack(b"\x01")

    with pytest.raises(pak.util.BufferOutOfDataError):
        TestAttr.unpack(b"\x01")

    Utf8Char = pak.Char("utf-8")
    pak.test.type_behavior(
        Utf8Char[None],

        ("ab", b"ab"),

        static_size = None,
        default     = "",
    )
