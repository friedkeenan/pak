import inspect
import pytest
from pak import *

def test_subclasses():
    class Root:
        pass

    class Child1(Root):
        pass

    class Child2(Root):
        pass

    class GrandChild1(Child1):
        pass

    assert util.subclasses(Root) == {Child1, Child2, GrandChild1}

def test_annotations():
    def test_empty_callable(x):
        pass

    def test_annotated_callable(x: 1):
        pass

    assert util.annotations(test_empty_callable)     == {}
    assert util.annotations(test_annotated_callable) == {"x": 1}

    class TestEmptyClass:
        pass

    class TestAnnotatedClass:
        x: 1

    class TestEmptyChildClass(TestAnnotatedClass):
        pass

    assert util.annotations(TestEmptyClass)      == {}
    assert util.annotations(TestAnnotatedClass)  == {"x": 1}
    assert util.annotations(TestEmptyChildClass) == {}

    from . import empty_module
    from . import annotated_module

    assert util.annotations(empty_module)     == {}
    assert util.annotations(annotated_module) == {"x": 1}

def test_bind_annotations():
    def test_basic(x, y, z):
        pass

    def test_keyword_required(x, y, *, z):
        pass

    def test_positional_only(x, y, z):
        pass

    # Python 3.7 can't define positional-only arguments
    # in pure python, so we manipulate the signature instead.
    test_positional_only.__signature__ = inspect.Signature(
        parameters = [
            inspect.Parameter("x", kind=inspect.Parameter.POSITIONAL_ONLY),
            inspect.Parameter("y", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD),
            inspect.Parameter("z", kind=inspect.Parameter.POSITIONAL_OR_KEYWORD),
        ],
    )

    def test_var_args(x: 1, y: 2, *args: 3, z: 4):
        pass

    def test_var_kwargs(x: 1, y: 2, *, z: 3, **kwargs: 4):
        pass

    def test_var_both(x: 1, y: 2, *args: 3, z: 4, **kwargs: 5):
        pass

    with pytest.raises(TypeError, match="Invalid keyword"):
        util.bind_annotations(test_basic, 1, 2, 3, blah=4)

    with pytest.raises(TypeError, match="Too many positional"):
        util.bind_annotations(test_basic, 1, 2, 3, 4)

    with pytest.raises(TypeError, match="Too many positional"):
        util.bind_annotations(test_keyword_required, 1, 2, 3)

    with pytest.raises(TypeError, match="Positional only"):
        util.bind_annotations(test_positional_only, x=1, y=2, z=3)

    args_annotations, kwargs_annotations = util.bind_annotations(test_var_args, 1, 2, 3, 4, z=5)
    assert len(args_annotations)   == 4
    assert len(kwargs_annotations) == 1

    assert (
        args_annotations[0] == (1, 1) and
        args_annotations[1] == (2, 2) and
        args_annotations[2] == (3, 3) and
        args_annotations[3] == (4, 3)
    )

    assert kwargs_annotations["z"] == (5, 4)

    args_annotations, kwargs_annotations = util.bind_annotations(test_var_kwargs, 1, 2, z=3, blah=4, other=5)
    assert len(args_annotations)   == 2
    assert len(kwargs_annotations) == 3

    assert (
        args_annotations[0] == (1, 1) and
        args_annotations[1] == (2, 2)
    )

    assert (
        kwargs_annotations["z"]     == (3, 3) and
        kwargs_annotations["blah"]  == (4, 4) and
        kwargs_annotations["other"] == (5, 4)
    )

    args_annotations, kwargs_annotations = util.bind_annotations(test_var_both, 1, 2, 3, 4, z=5, blah=6, other=7)
    assert len(args_annotations)   == 4
    assert len(kwargs_annotations) == 3

    assert (
        args_annotations[0] == (1, 1) and
        args_annotations[1] == (2, 2) and
        args_annotations[2] == (3, 3) and
        args_annotations[3] == (4, 3)
    )

    assert (
        kwargs_annotations["z"]     == (5, 4) and
        kwargs_annotations["blah"]  == (6, 5) and
        kwargs_annotations["other"] == (7, 5)
    )
