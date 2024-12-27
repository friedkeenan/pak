import pak

async def test_defaulted():
    DefaultedInt8 = pak.Defaulted(pak.Int8, 1)

    assert DefaultedInt8.mro() == [DefaultedInt8, pak.Int8, pak.StructType, pak.Defaulted, pak.Type, object]

    await pak.test.type_behavior_both(
        DefaultedInt8,

        (0, b"\x00"),
        (1, b"\x01"),
        (2, b"\x02"),

        static_size = 1,
        alignment   = 1,
        default     = 1,
    )
