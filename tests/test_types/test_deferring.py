import pak
import pytest

class DeferringContext(pak.Packet.Context):
    def __init__(self, *, use_raw_byte):
        self.use_raw_byte = use_raw_byte

        super().__init__()

    def __hash__(self):
        return hash(self.use_raw_byte)

    def __eq__(self, other):
        if not isinstance(other, DeferringContext):
            return NotImplemented

        return self.use_raw_byte == other.use_raw_byte

class DeferringTest(pak.DeferringType):
    @classmethod
    def _defer_to(cls, *, ctx):
        # We defer to either 'RawByte' or 'UInt16'.

        if ctx.use_raw_byte:
            return pak.RawByte

        return pak.UInt16

ctx_raw_byte = pak.Type.Context(ctx=DeferringContext(use_raw_byte=True))
ctx_uint16   = pak.Type.Context(ctx=DeferringContext(use_raw_byte=False))

async def test_deferring_type():
    await pak.test.type_behavior_both(
        DeferringTest,

        (b"\xAA", b"\xAA"),

        static_size = 1,
        alignment   = 1,
        default     = b"\x00",

        ctx = ctx_raw_byte,
    )

    await pak.test.type_behavior_both(
        DeferringTest,

        (1, b"\x01\x00"),

        static_size = 2,
        alignment   = 2,
        default     = 0,

        ctx = ctx_uint16,
    )

async def test_deferring_type_array():
    await pak.test.type_behavior_both(
        DeferringTest[2],

        (b"\xAA\xBB", b"\xAA\xBB"),

        static_size = 2,
        alignment   = 1,
        default     = b"\x00\x00",

        ctx = ctx_raw_byte,
    )

    await pak.test.type_behavior_both(
        DeferringTest[2],

        ([1, 2], b"\x01\x00\x02\x00"),

        static_size = 4,
        alignment   = 2,
        default     = [0, 0],

        ctx = ctx_uint16,
    )

    await pak.test.type_behavior_both(
        DeferringTest[pak.Int8],

        (b"\xAA\xBB", b"\x02\xAA\xBB"),
        (b"",         b"\x00"),

        static_size = None,
        default     = b"",

        ctx = ctx_raw_byte,
    )

    await pak.test.type_behavior_both(
        DeferringTest[pak.Int8],

        ([1, 2], b"\x02\x01\x00\x02\x00"),
        ([],     b"\x00"),

        static_size = None,
        default     = [],

        ctx = ctx_uint16,
    )

    await pak.test.type_behavior_both(
        DeferringTest[None],

        (b"\xAA\xBB\xCC", b"\xAA\xBB\xCC"),

        static_size = None,
        default     = b"",

        ctx = ctx_raw_byte,
    )

    await pak.test.type_behavior_both(
        DeferringTest[None],

        ([1, 2, 3], b"\x01\x00\x02\x00\x03\x00"),

        static_size = None,
        default     = [],

        ctx = ctx_uint16,
    )

    class TestAttr(pak.Packet):
        length: pak.Int8
        array:  DeferringTest["length"]


    assert TestAttr(length=2, ctx=ctx_raw_byte.packet_ctx).array == b"\x00\x00"

    await pak.test.packet_behavior_both(
        (TestAttr(length=2, array=b"\xAA\xBB"), b"\x02\xAA\xBB"),

        ctx = ctx_raw_byte.packet_ctx,
    )

    assert TestAttr(length=2, ctx=ctx_uint16.packet_ctx).array == [0, 0]

    await pak.test.packet_behavior_both(
        (TestAttr(length=2, array=[1, 2]), b"\x02\x01\x00\x02\x00"),

        ctx = ctx_uint16.packet_ctx,
    )

async def test_deferring_type_cannot_defer_unbounded_array():
    # An error should be raised when there is no Type to defer
    # to, instead of being suppressed like other exceptions.

    with pytest.raises(pak.DeferringType.UnableToDeferError, match="not implemented"):
        pak.DeferringType[None].unpack(b"")

    with pytest.raises(pak.DeferringType.UnableToDeferError, match="not implemented"):
        await pak.DeferringType[None].unpack_async(b"")
