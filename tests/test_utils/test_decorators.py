import inspect
import sys
import pak
import pytest

def test_uncustomized_cache():
    @pak.util.cache
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
    @pak.util.cache(force_hashable=False)
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
    @pak.util.cache(max_size=1)
    def test_max_size(x):
        return object()

    obj = test_max_size(1)

    assert test_max_size(1) is     obj
    assert test_max_size(2) is not obj

    # Make sure the old parameter is now uncached.
    assert test_max_size(1) is not obj

def test_class_or_instance_method():
    class Test:
        @pak.util.class_or_instance_method
        def method(cls):
            """docstring"""

            return "class"

        @method.instance_method
        def method(self):
            return "instance"

    assert inspect.getattr_static(Test, "method").__doc__ == "docstring"

    assert Test.method()   == "class"
    assert Test().method() == "instance"

    # The 'TypeError' we raise gets turned into a 'RuntimeError' until Python 3.12.
    with pytest.raises(TypeError if sys.version_info.minor >= 12 else RuntimeError):
        class MissingInstanceMethod:
            @pak.util.class_or_instance_method
            def method(cls):
                pass

def test_class_or_instance_method_copy():
    class Test:
        @pak.util.class_or_instance_method
        def method_orig(cls):
            return "orig class"

        @method_orig.instance_method
        def method_orig(self):
            return "orig instance"

        @method_orig.instance_method
        def method_new(self):
            return "new instance"

        @method_new.class_method
        def method_newer(cls):
            return "newer class"

    assert inspect.getattr_static(Test, "method_orig")  is not inspect.getattr_static(Test, "method_new")
    assert inspect.getattr_static(Test, "method_newer") is not inspect.getattr_static(Test, "method_new")

    assert Test.method_orig()   == "orig class"
    assert Test().method_orig() == "orig instance"

    assert Test.method_new()   == "orig class"
    assert Test().method_new() == "new instance"

    assert Test.method_newer()   == "newer class"
    assert Test().method_newer() == "new instance"

def test_class_or_instance_method_inherit():
    class inherited_class_or_instance_method(pak.util.class_or_instance_method):
        pass

    class Test:
        @inherited_class_or_instance_method
        def method(cls):
            pass

        @method.instance_method
        def method(self):
            pass

    assert isinstance(inspect.getattr_static(Test, "method"), inherited_class_or_instance_method)
