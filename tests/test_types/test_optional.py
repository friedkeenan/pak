import pak

def test_optional_specializations():
    assert issubclass(pak.Optional.PrefixChecked,   pak.Optional)
    assert issubclass(pak.Optional.Unchecked,       pak.Optional)
    assert issubclass(pak.Optional.FunctionChecked, pak.Optional)

    assert issubclass(pak.Optional(pak.Int8, pak.Bool),       pak.Optional.PrefixChecked)
    assert issubclass(pak.Optional(pak.Int8),                 pak.Optional.Unchecked)
    assert issubclass(pak.Optional(pak.Int8, "attr"),         pak.Optional.FunctionChecked)
    assert issubclass(pak.Optional(pak.Int8, lambda p: True), pak.Optional.FunctionChecked)

async def test_optional():
    TestPrefix = pak.Optional(pak.Int8, pak.Bool)
    await pak.test.type_behavior_both(
        TestPrefix,

        (None, b"\x00"),
        (0,    b"\x01\x00"),

        static_size = None,
        default     = None,
    )

    TestUnchecked = pak.Optional(pak.Int8)
    await pak.test.type_behavior_both(
        TestUnchecked,

        (None, b""),
        (0,    b"\x00"),

        static_size = None,
        default     = None,
    )

    # NOTE: Conveniently, testing string
    # sizes will also test function checking.
    TestFunction = pak.Optional(pak.Int8, "test")

    class TestAttr(pak.Packet):
        test:     pak.Bool
        optional: TestFunction

    assert TestAttr(test=False).optional is None
    assert TestAttr(test=True).optional  == 0

    await pak.test.packet_behavior_both(
        (TestAttr(test=False), b"\x00"),
        (TestAttr(test=True),  b"\x01\x00"),
    )

    ctx_false = TestAttr(test=False).type_ctx(None)
    ctx_true  = TestAttr(test=True).type_ctx(None)

    await pak.test.type_behavior_both(
        TestFunction,

        (None, b""),

        static_size = None,
        default     = None,
        ctx         = ctx_false,
    )

    await pak.test.type_behavior_both(
        TestFunction,

        (0, b"\x00"),

        static_size = None,
        default     = 0,
        ctx         = ctx_true,
    )
