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

    TestStrictPrefixed = pak.PrefixedString(pak.UInt8, errors="strict")

    with pytest.raises(UnicodeDecodeError):
        TestStrictPrefixed.unpack(b"\x01\xFF")

def test_terminated_string():
    pak.test.type_behavior(
        pak.TerminatedString,

        ("abc", b"abc\x00"),
        ("ab",  b"ab\x00"),
        ("",    b"\x00"),

        ("\u200B", b"\xE2\x80\x8B\x00"),

        static_size = None,
        default     = "",
    )

    # Invalid bytes get replaced.
    assert pak.TerminatedString.unpack(b"\xFF\x00") == "\uFFFD"

    with pytest.raises(pak.util.BufferOutOfDataError):
        pak.TerminatedString.unpack(b"Non-terminated string")

def test_terminated_string_alternate_terminator():
    with pytest.raises(ValueError, match="length"):
        pak.TerminatedString(terminator="ab")

    with pytest.raises(ValueError, match="length"):
        pak.TerminatedString(terminator="")

    pak.test.type_behavior(
        pak.TerminatedString(terminator="Z"),

        ("abc", b"abcZ"),
        ("ab",  b"abZ"),
        ("a",   b"aZ"),
        ("",    b"Z"),

        ("\u200B", b"\xE2\x80\x8BZ"),

        static_size = None,
        default     = "",
    )

def test_terminated_string_strict_errors():
    TestString = pak.TerminatedString(errors="strict")

    with pytest.raises(UnicodeDecodeError):
        TestString.unpack(b"\xFF\x00")

def test_static_terminated_string():
    TestString = pak.StaticTerminatedString(4)

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

    # An error is raised if there is not enough data.
    with pytest.raises(pak.util.BufferOutOfDataError):
        TestString.unpack(b"ab\x00")

    with pytest.raises(ValueError, match="terminator"):
        TestString.unpack(b"abcd")

    # Make sure we consider the terminator when seeing
    # if a string is too large to pack.
    with pytest.raises(ValueError, match="too large"):
        TestString.pack("abcd")

    # Make sure we don't just raise an error when the string
    # is too long but rather when the packed data would be
    # too large.
    with pytest.raises(ValueError, match="too large"):
        TestString.pack("\u200B\u200B")

def test_static_terminated_string_alternate_terminator():
    with pytest.raises(ValueError, match="length"):
        pak.StaticTerminatedString(4, terminator="ab")

    with pytest.raises(ValueError, match="length"):
        pak.StaticTerminatedString(4, terminator="")

    pak.test.type_behavior(
        pak.StaticTerminatedString(4, terminator="Z"),

        ("abc", b"abcZ"),
        ("ab",  b"abZ\x00"),
        ("a",   b"aZ\x00\x00"),
        ("",    b"Z\x00\x00\x00"),

        ("\u200B", b"\xE2\x80\x8BZ"),

        static_size = 4,
        alignment   = 1,
        default     = "",
    )

def test_static_terminated_string_strict_errors():
    TestString = pak.StaticTerminatedString(4, errors="strict")

    with pytest.raises(UnicodeDecodeError):
        TestString.unpack(b"\xFF\x00\x00\x00")

    # Make sure invalid bytes after the terminator don't raise errors.
    assert TestString.unpack(b"a\x00\xFF\x00") == "a"

def test_static_terminated_string_alignment():
    SameEncoding = pak.StaticTerminatedString(4, encoding="utf-8")

    assert SameEncoding.alignment() == 1

    SameEncodingUnspecified = pak.StaticTerminatedString(4)
    assert SameEncodingUnspecified.alignment() == 1

    DifferentEncoding = pak.StaticTerminatedString(4, encoding="utf-16-le")

    with pytest.raises(TypeError, match="no alignment"):
        DifferentEncoding.alignment()

    AlignmentSpecified = pak.StaticTerminatedString(4, encoding="utf-16-le", alignment=2)
    assert AlignmentSpecified.alignment() == 2
