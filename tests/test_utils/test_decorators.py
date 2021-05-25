import pytest
from pak import *

def test_cache():
    @util.cache
    def test(x):
        return object()

    obj = test(1)
    assert test(1) is     obj
    assert test(2) is not obj

    with pytest.raises(TypeError, match="unhashable"):
        test({})

    @util.cache(force_hashable=False)
    def test_hashable(x):
        return object()

    # Unhashable type.
    obj = test_hashable({})
    assert test_hashable({}) is not obj
