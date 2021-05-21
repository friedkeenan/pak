import sys
import pytest
from pak import *

def test_arg_annoations():
    def test_basic(x, y, z):
        pass

    def test_keyword_required(x, y, *, z):
        pass

    def test_var_args(x: 1, y: 2, *args: 3, z: 4):
        pass

    def test_var_kwargs(x: 1, y: 2, *, z: 3, **kwargs: 4):
        pass

    def test_var_both(x: 1, y: 2, *args: 3, z: 4, **kwargs: 5):
        pass

    with pytest.raises(TypeError, match="Invalid keyword"):
        util.arg_annotations(test_basic, 1, 2, 3, blah=4)

    with pytest.raises(TypeError, match="Too many positional"):
        util.arg_annotations(test_basic, 1, 2, 3, 4)

    with pytest.raises(TypeError, match="Too many positional"):
        util.arg_annotations(test_keyword_required, 1, 2, 3)

    # Python 3.7 can't define positonal arguments
    # in pure python.
    if sys.version_info.minor > 7:
        def test_positional_only(x, /, y, z):
            pass

        with pytest.raises(TypeError, match="Positional only"):
            util.arg_annotations(test_positional_only, x=1, y=2, z=3)

    args_annotations, kwargs_annotations = util.arg_annotations(test_var_args, 1, 2, 3, 4, z=5)
    assert len(args_annotations)   == 4
    assert len(kwargs_annotations) == 1

    assert (
        args_annotations[0] == (1, 1) and
        args_annotations[1] == (2, 2) and
        args_annotations[2] == (3, 3) and
        args_annotations[3] == (4, 3)
    )

    assert kwargs_annotations["z"] == (5, 4)

    args_annotations, kwargs_annotations = util.arg_annotations(test_var_kwargs, 1, 2, z=3, blah=4, other=5)
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

    args_annotations, kwargs_annotations = util.arg_annotations(test_var_both, 1, 2, 3, 4, z=5, blah=6, other=7)
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
