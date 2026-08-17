import pytest
from pydantic import ValidationError

from opengrader.config import TestConfig as GraderTestConfig

pytestmark = pytest.mark.unit


def test_partial_credit_defaults_to_empty_mapping() -> None:
    test = GraderTestConfig(name="binary", command="true")

    assert test.partial_credit == {}


def test_partial_credit_accepts_nonzero_exit_codes_and_fractions() -> None:
    test = GraderTestConfig(
        name="rubric", command="grade", points=8, partial_credit={2: 0.75, 3: 0.25}
    )

    assert test.partial_credit == {2: 0.75, 3: 0.25}


@pytest.mark.parametrize(
    "mapping",
    [
        {0: 0.5},
        {-1: 0.5},
        {256: 0.5},
        {1: -0.1},
        {1: 1.1},
    ],
)
def test_partial_credit_rejects_invalid_mapping(mapping: dict[int, float]) -> None:
    with pytest.raises(ValidationError):
        GraderTestConfig(name="invalid", command="grade", partial_credit=mapping)
