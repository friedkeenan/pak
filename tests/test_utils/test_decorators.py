import pytest
from pak import *

def test_uncustomized_cache():
    @util.cache
    def test_uncustomized(x):
        return object()

    obj = test_uncustomized(1)

    assert test_uncustomized(1) is     obj
    assert test_uncustomized(2) is not obj

    # Make sure the old parameter is still cached.
    assert test_uncustomized(1) is obj

    with pytest.raises(TypeError, match="unhashable"):
        test_uncustomized({})

def test_force_hashable_cache():
    @util.cache(force_hashable=False)
    def test_hashable(x):
        return object()

    obj = test_hashable(1)

    assert test_hashable(1) is     obj
    assert test_hashable(2) is not obj

    # Make sure the old parameter is still cached.
    assert test_hashable(1) is obj

    # Unhashable type.
    obj = test_hashable({})

    assert test_hashable({}) is not obj

def test_max_size_cache():
    @util.cache(max_size=1)
    def test_max_size(x):
        return object()

    obj = test_max_size(1)

    assert test_max_size(1) is     obj
    assert test_max_size(2) is not obj

    # Make sure the old parameter is now uncached.
    assert test_max_size(1) is not obj

def test_class_or_instance_method():
    class Test:
        @util.class_or_instance_method
        def method(cls):
            return "class"

        @method.instance
        def method(self):
            return "instance"

    assert Test.method()   == "class"
    assert Test().method() == "instance"

    # The 'TypeError' we raise gets turned into a 'RuntimeError'.
    with pytest.raises(RuntimeError,):
        class MissingInstanceMethod:
            @util.class_or_instance_method
            def method(cls):
                pass
