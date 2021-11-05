from pak import *

def test_dynamic_value():
    assert DynamicValue(1) == 1

    class IntDynamicValue(DynamicValue):
        _type = int

        def __init__(self, initial_value):
            self.initial_value = initial_value

        def get(self, *, ctx=None):
            return self.initial_value * 2

    # Automatically enabled.
    assert IntDynamicValue._enabled

    v = DynamicValue(1)
    assert isinstance(v, IntDynamicValue)

    assert v.get() == 2
    assert DynamicValue(2).get() == 4

    # Test disabling.
    IntDynamicValue.disable()

    assert not IntDynamicValue._enabled

    assert DynamicValue(1) == 1

    # Test re-enabling.
    IntDynamicValue.enable()

    assert IntDynamicValue._enabled
    assert isinstance(DynamicValue(1), IntDynamicValue)

    IntDynamicValue.disable()

def test_dynamic_value_context():
    class StringDynamicValue(DynamicValue):
        _type = str

        def __init__(self, string):
            self.string = string

        def get(self, *, ctx=None):
            return self.string.upper()

    with StringDynamicValue.context():
        v = DynamicValue("abc")

        assert isinstance(v, StringDynamicValue)
        assert v.get() == "ABC"

    assert not StringDynamicValue._enabled

    assert DynamicValue("abc") == "abc"

def test_explciit_disable():
    class DummyDynamicValue(DynamicValue):
        _type = str

        _enabled = False

    assert not DummyDynamicValue._enabled

    assert DynamicValue("abc") == "abc"
