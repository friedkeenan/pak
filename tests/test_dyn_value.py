from pak import *

def test_dynamic_value():
    assert DynamicValue(1) == 1

    class IntDynamicValue(DynamicValue):
        _type = int

        def __init__(self, initial_value):
            self.initial_value = initial_value

        def get(self, *, ctx=None):
            return self.initial_value * 2

    v = DynamicValue(1)
    assert isinstance(v, IntDynamicValue)

    assert v.get() == 2
    assert DynamicValue(2).get() == 4

    # Disable IntDynamicValue
    IntDynamicValue._type = None

    assert DynamicValue(1) == 1
