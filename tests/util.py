def assert_type_marshal(type_cls, *values_and_data, ctx=None):
    for value, data in values_and_data:
        data_from_value = type_cls.pack(value, ctx=ctx)
        value_from_data = type_cls.unpack(data, ctx=ctx)

        assert data_from_value == data
        assert value_from_data == value

def assert_type_marshal_func(*args, **kwargs):
    # Use this if you only need to compare values
    # and raw data and can compare the values using
    # equality.
    #
    # For anything else, you should create your own
    # function, potentially using assert_type_marshal.

    return lambda: assert_type_marshal(*args, **kwargs)

def assert_packet_marshal(*values_and_data, ctx=None):
    for value, data in values_and_data:
        data_from_value = value.pack(ctx=ctx)
        value_from_data = value.unpack(data, ctx=ctx)

        assert data_from_value == data
        assert value_from_data == value

def assert_packet_marshal_func(*args, **kwargs):
    # Use this if you only need to compare values
    # and raw data and can compare the values using
    # equality.
    #
    # For anything else, you should create your own
    # function, potentially using assert_packet_marshal.

    return lambda: assert_packet_marshal(*args, **kwargs)
