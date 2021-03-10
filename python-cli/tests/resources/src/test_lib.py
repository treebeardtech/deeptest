import pytest

from .lib import divide


def test_divide():
    assert divide(1.0, 2) == 0.5


@pytest.mark.parametrize("denom", [(3.0), (0)])
def test_divide2(denom: float):
    assert divide(1.0, denom) == 1 / 3
