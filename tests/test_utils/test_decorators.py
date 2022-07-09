import inspect
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
    with pytest.raises(RuntimeError):
        class MissingInstanceMethod:
            @util.class_or_instance_method
            def method(cls):
                pass

def test_class_or_instance_method_descriptor_propagate():
    class Test:
        @util.class_or_instance_method
        @property
        def attr(cls):
            return "class"

        @attr.instance
        @property
        def attr(self):
            return "instance"

    assert Test.attr   == "class"
    assert Test().attr == "instance"

def test_class_or_instance_method_copy():
    class Test:
        @util.class_or_instance_method
        def method_orig(cls):
            return "orig class"

        @method_orig.instance
        def method_orig(self):
            return "orig instance"

        @method_orig.instance
        def method_new(self):
            return "new instance"

    assert inspect.getattr_static(Test, "method_orig") is not inspect.getattr_static(Test, "method_new")

    assert Test.method_orig()   == "orig class"
    assert Test().method_orig() == "orig instance"

    assert Test.method_new()   == "orig class"
    assert Test().method_new() == "new instance"
