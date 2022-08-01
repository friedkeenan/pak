import pak
import pytest

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

    # Invalid bytes get replaced.
    assert TestPrefixed.unpack(b"\x01\xFF") == "\uFFFD"

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

    # Invalid bytes get replaced.
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
