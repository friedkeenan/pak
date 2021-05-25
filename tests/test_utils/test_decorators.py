from pak import *

def test_cache():
    @util.cache
    def test(x):
        return object()

    obj = test(1)
    assert test(1) is     obj
    assert test(2) is not obj

    # Unhashable type.
    obj = test({})
    assert test({}) is not obj
